"""
Face Detection Service - YOLO-based face detection with AWS Rekognition integration

This service runs a continuous loop detecting faces using YOLO v8, and when a face
is consistently detected (4 consecutive frames at 2Hz = 2 seconds), it captures
the face and sends it to AWS Rekognition for identification.
"""

import cv2
import numpy as np
import base64
import time
import asyncio
from typing import Optional
from ultralytics import YOLO
from config import (
    FACE_DETECTION_ENABLED,
    FACE_DETECTION_FPS,
    FACE_CONFIRMATION_COUNT,
    FACE_COOLDOWN_SECONDS,
    YOLO_MODEL,
    CAMERA_INDEX,
    YOLO_CONFIDENCE_THRESHOLD
)

# Try to import picamera2 (for Raspberry Pi)
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False


class FaceDetectionService:
    """
    YOLO-based face detection service with AWS Rekognition integration.
    
    Flow:
    1. YOLO detects "person" at 2Hz
    2. After 4 consecutive detections (2 seconds), capture face
    3. Send to FastAPI /face/recognize endpoint
    4. Display result on OLED
    """
    
    def __init__(self):
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.model = None
        self.cap = None
        self.picam = None
        self.use_picamera = False
        
        # Detection state
        self.consecutive_detections = 0
        self.last_recognition_time = 0
        
        # Timing
        self.detection_interval = 1.0 / FACE_DETECTION_FPS  # 0.5 seconds for 2Hz
    
    async def start(self):
        """Start the face detection service"""
        if not FACE_DETECTION_ENABLED:
            print("⏸️  Face detection is disabled in config")
            return
        
        if self.is_running:
            print("⚠️  Face detection is already running")
            return
        
        # Initialize YOLO model and camera
        try:
            print(f"🔍 Loading YOLO model: {YOLO_MODEL}")
            self.model = YOLO(YOLO_MODEL)
            print(f"✅ YOLO model loaded successfully")
            
            # Try picamera2 first (for Raspberry Pi), then fall back to OpenCV
            if PICAMERA2_AVAILABLE:
                try:
                    print(f"📷 Attempting to open Pi Camera using picamera2...")
                    self.picam = Picamera2()
                    
                    # Configure camera for 640x480 (matches our resize target)
                    config = self.picam.create_preview_configuration(
                        main={"size": (640, 480), "format": "RGB888"}
                    )
                    self.picam.configure(config)
                    self.picam.start()
                    
                    # Give camera time to initialize
                    time.sleep(2)
                    
                    self.use_picamera = True
                    print(f"✅ Pi Camera opened successfully (picamera2)")
                    
                except Exception as e:
                    print(f"⚠️  Failed to open picamera2: {e}")
                    print(f"   Falling back to OpenCV...")
                    self.use_picamera = False
            
            # Fallback to OpenCV (for USB cameras or if picamera2 fails)
            if not self.use_picamera:
                print(f"📷 Opening camera using OpenCV (index: {CAMERA_INDEX})")
                self.cap = cv2.VideoCapture(CAMERA_INDEX)
                
                if not self.cap.isOpened():
                    print(f"❌ Failed to open camera at index {CAMERA_INDEX}")
                    return
                
                print(f"✅ Camera opened successfully (OpenCV)")
            
        except Exception as e:
            print(f"❌ Failed to initialize face detection: {e}")
            import traceback
            traceback.print_exc()
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._detection_loop())
        
        print(f"▶️  Face detection started")
        print(f"   Detection rate: {FACE_DETECTION_FPS}Hz")
        print(f"   Confidence threshold: {YOLO_CONFIDENCE_THRESHOLD:.2f}")
        print(f"   Confirmation: {FACE_CONFIRMATION_COUNT} consecutive detections")
        print(f"   Cooldown: {FACE_COOLDOWN_SECONDS} seconds")
    
    async def stop(self):
        """Stop the face detection service"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        # Release camera resources
        if self.use_picamera and self.picam:
            try:
                self.picam.stop()
            except:
                pass
        
        if self.cap:
            self.cap.release()
        
        print("⏹️  Face detection stopped")
    
    async def _detection_loop(self):
        """Main detection loop - runs continuously"""
        print("🔄 Face detection loop started")
        
        while self.is_running:
            try:
                loop_start = time.time()
                
                # Process one frame
                await self._process_frame()
                
                # Wait for next detection interval
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.detection_interval - elapsed)
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Error in detection loop: {e}")
                await asyncio.sleep(self.detection_interval)
    
    async def _process_frame(self):
        """Process a single frame for face detection"""
        
        # Get frame from appropriate camera source
        if self.use_picamera:
            try:
                # Capture frame from picamera2
                frame = self.picam.capture_array()
                
                # picamera2 returns RGB, OpenCV uses BGR
                frame_resized = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Already at 640x480 from config
            except Exception as e:
                print(f"⚠️  Failed to capture frame from picamera2: {e}")
                return
        else:
            # Capture from OpenCV
            ret, frame = self.cap.read()
            if not ret:
                print("⚠️  Failed to read frame from camera")
                return
            
            # Resize frame for faster processing
            frame_resized = cv2.resize(frame, (640, 480))
        
        # Run YOLO detection
        results = self.model(frame_resized, stream=True, verbose=False)
        
        person_detected = False
        valid_detections = []
        
        # Collect all valid detections (above confidence threshold)
        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                name = self.model.names[cls]
                confidence = float(box.conf[0])
                
                # Only process "person" class with sufficient confidence
                if name == "person" and confidence >= YOLO_CONFIDENCE_THRESHOLD:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    box_area = (x2 - x1) * (y2 - y1)
                    
                    valid_detections.append({
                        'confidence': confidence,
                        'box': (x1, y1, x2, y2),
                        'area': box_area
                    })
        
        # If we have valid detections, use only the most confident one
        faces_to_process = []
        if valid_detections:
            person_detected = True
            
            # Sort by confidence (highest first)
            valid_detections.sort(key=lambda d: d['confidence'], reverse=True)
            
            # Take only the most confident detection
            best_detection = valid_detections[0]
            x1, y1, x2, y2 = best_detection['box']
            
            # Extract face crop (upper half of person box)
            h = y2 - y1
            face_crop = frame_resized[y1:y1 + h//2, x1:x2]
            
            faces_to_process.append(face_crop)
            
            # Log the detection
            print(f"👤 Person detected (confidence: {best_detection['confidence']:.2f}, " +
                  f"area: {best_detection['area']} px²)")
        
        # Update detection counter
        if person_detected:
            self.consecutive_detections += 1
            print(f"   Counter: {self.consecutive_detections}/{FACE_CONFIRMATION_COUNT}")
        else:
            if self.consecutive_detections > 0:
                print(f"   Detection reset (no person found)")
            self.consecutive_detections = 0
        
        # Check if we should trigger recognition
        if self.consecutive_detections >= FACE_CONFIRMATION_COUNT:
            # Check cooldown
            time_since_last = time.time() - self.last_recognition_time
            
            if time_since_last >= FACE_COOLDOWN_SECONDS:
                print(f"✅ Face confirmed! Processing {len(faces_to_process)} face(s)...")
                
                # Process all detected faces sequentially
                for i, face_crop in enumerate(faces_to_process, 1):
                    print(f"   Processing face {i}/{len(faces_to_process)}...")
                    await self._recognize_face(face_crop)
                
                # Reset counter and update last recognition time
                self.consecutive_detections = 0
                self.last_recognition_time = time.time()
            else:
                remaining = FACE_COOLDOWN_SECONDS - time_since_last
                print(f"⏳ Cooldown active ({remaining:.1f}s remaining)")
                # Keep counter at threshold during cooldown
                self.consecutive_detections = FACE_CONFIRMATION_COUNT
    
    async def _recognize_face(self, face_image):
        """
        Send face image to AWS Rekognition for identification
        
        Args:
            face_image: OpenCV image (numpy array) of the face
        """
        try:
            # Encode face image to JPEG
            _, buffer = cv2.imencode('.jpg', face_image)
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            print(f"📸 Captured face image ({len(buffer)} bytes)")
            
            # Import services here to avoid circular imports
            from services.face_recognition_service import get_face_recognition_service
            from services.oled_display import get_oled_service
            
            # Call face recognition API
            face_service = get_face_recognition_service()
            result = await face_service.recognize_face(
                image_base64=image_base64,
                min_confidence=85.0
            )
            
            # Display result
            if result.get("recognized"):
                name = result.get("name")
                relationship = result.get("relationship")
                similarity = result.get("similarity", 0)
                
                print("\n" + "="*60)
                print("🎉 FACE RECOGNIZED!")
                print(f"   Name: {name}")
                print(f"   Relationship: {relationship}")
                print(f"   Confidence: {similarity:.1f}%")
                print("="*60 + "\n")
                
                # Display on OLED
                try:
                    oled = get_oled_service()
                    display_message = f"Hello {name}!"
                    if relationship:
                        display_message += f"\n({relationship})"
                    
                    oled.display_wrapped_message(
                        message=display_message,
                        max_chars_per_line=16,
                        font_size=14,
                        should_blink=True,
                        display_time=10
                    )
                except Exception as e:
                    print(f"⚠️  Could not display on OLED: {e}")
            
            else:
                # No match - stay silent as requested
                print("   No match found in database (staying silent)")
            
        except Exception as e:
            print(f"❌ Error during face recognition: {e}")


# Global service instance
_face_detection_instance: Optional[FaceDetectionService] = None


def get_face_detection_service() -> FaceDetectionService:
    """Get the global face detection service instance"""
    global _face_detection_instance
    if _face_detection_instance is None:
        _face_detection_instance = FaceDetectionService()
    return _face_detection_instance

