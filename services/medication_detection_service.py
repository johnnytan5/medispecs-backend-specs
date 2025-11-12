"""
Medication Detection Service - YOLO-based medication bottle detection with OpenAI Vision verification
Uses custom YOLO model to detect medication bottles, then verifies with OpenAI Vision API
"""
import cv2
import numpy as np
import base64
import asyncio
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from ultralytics import YOLO
import openai


class MedicationDetectionService:
    """
    Medication bottle detection service
    
    Features:
    - Uses custom YOLO model for medication bottle detection
    - Shares frames with face detection service
    - Captures photo when bottle detected
    - Fetches reference photo from Lambda
    - Compares with OpenAI Vision API
    - Provides TTS + OLED feedback
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.is_detecting = False
        self.detection_task: Optional[asyncio.Task] = None
        
        # YOLO model
        self.model: Optional[YOLO] = None
        self.model_path: Optional[str] = None
        self.confidence_threshold = 0.05
        
        # Current detection session
        self.current_detection: Optional[Dict[str, Any]] = None
        
        # OpenAI client
        self.openai_client = None
        self.openai_api_key = None
        
        # Frame sharing (from face detection service)
        self.face_detection_service = None  # Will be set by main.py
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize medication detection service
        
        Args:
            config: Dictionary with detection settings from config.py
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Load configuration
            self.model_path = config.get('MEDICATION_YOLO_MODEL', 'medication_model.pt')
            self.confidence_threshold = config.get('MEDICATION_YOLO_CONFIDENCE', 0.05)
            
            # Load OpenAI API key
            import os
            from dotenv import load_dotenv
            load_dotenv()
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not self.openai_api_key:
                print("⚠️  OPENAI_API_KEY not found, medication verification will be disabled")
            else:
                self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
            
            # Load YOLO model
            if Path(self.model_path).exists():
                print(f"🔍 Loading medication YOLO model: {self.model_path}")
                self.model = YOLO(self.model_path)
                print(f"✅ Medication YOLO model loaded successfully")
            else:
                print(f"⚠️  Medication model not found: {self.model_path}")
                print(f"   Place your trained model at: {self.model_path}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Medication detection initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def start_detection(self, medication_id: str, medication_name: str, 
                             reference_photo_url: str, window_duration_seconds: int = 300):
        """
        Start medication detection session
        
        Args:
            medication_id: Medication ID
            medication_name: Medication name
            reference_photo_url: URL to reference photo from Lambda
            window_duration_seconds: Detection window duration (default 5 minutes = 300s)
        """
        if self.is_detecting:
            print("⚠️  Medication detection already active")
            return
        
        if not self.model:
            print("❌ Medication model not loaded")
            return
        
        if not self.face_detection_service:
            print("❌ Face detection service not available (needed for frame sharing)")
            return
        
        self.is_detecting = True
        start_time = datetime.now()
        self.current_detection = {
            'medication_id': medication_id,
            'medication_name': medication_name,
            'reference_photo_url': reference_photo_url,
            'start_time': start_time,
            'window_end': start_time.timestamp() + window_duration_seconds,
            'bottle_detected': False,
            'verification_complete': False
        }
        
        # Start detection loop
        self.detection_task = asyncio.create_task(self._detection_loop())
        
        print(f"🔍 Started medication detection for: {medication_name}")
        print(f"   Window duration: {window_duration_seconds}s")
    
    async def stop_detection(self):
        """Stop current detection session"""
        if not self.is_detecting:
            return
        
        self.is_detecting = False
        
        if self.detection_task:
            self.detection_task.cancel()
            try:
                await self.detection_task
            except asyncio.CancelledError:
                pass
        
        self.current_detection = None
        print("🛑 Medication detection stopped")
    
    async def _detection_loop(self):
        """
        Main detection loop
        Runs at ~2Hz (every 0.5 seconds) to detect medication bottles
        """
        detection_interval = 0.5  # 2Hz
        
        while self.is_detecting:
            try:
                # Check if window expired
                if time.time() >= self.current_detection['window_end']:
                    print(f"⏱️  Detection window expired")
                    await self._handle_no_detection()
                    break
                
                # Get latest frame from face detection service
                async with self.face_detection_service.frame_lock:
                    frame = self.face_detection_service.latest_frame
                
                if frame is None:
                    await asyncio.sleep(detection_interval)
                    continue
                
                # Run YOLO detection
                results = await asyncio.to_thread(self.model.predict, frame, conf=self.confidence_threshold, verbose=False)
                
                # Check for medication bottle detections
                if results and len(results) > 0:
                    boxes = results[0].boxes
                    
                    if len(boxes) > 0:
                        # Medication bottle detected!
                        print(f"💊 Medication bottle detected! ({len(boxes)} boxes)")
                        
                        # Capture frame and verify
                        await self._handle_bottle_detected(frame)
                        
                        # Stop detection after successful verification
                        if self.current_detection.get('verification_complete'):
                            break
                
                await asyncio.sleep(detection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Error in detection loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _handle_bottle_detected(self, frame: np.ndarray):
        """Handle medication bottle detection"""
        if self.current_detection.get('bottle_detected'):
            return  # Already processing
        
        self.current_detection['bottle_detected'] = True
        
        # Show "Verifying" message
        from services.oled_display import get_oled_service
        import config
        
        oled = get_oled_service()
        await asyncio.to_thread(oled.show_message, config.MEDICATION_OLED_VERIFYING)
        
        # Save captured frame
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        medication_id = self.current_detection['medication_id']
        photo_path = Path(f"medication_detections/{medication_id}_{timestamp}.jpg")
        photo_path.parent.mkdir(parents=True, exist_ok=True)
        
        cv2.imwrite(str(photo_path), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        print(f"📸 Captured medication photo: {photo_path}")
        
        # Fetch reference photo
        reference_photo_url = self.current_detection.get('reference_photo_url') or self.current_detection.get('photo_url')
        
        if not reference_photo_url:
            print(f"⚠️  No reference photo URL, skipping verification")
            # Record detection without verification
            from services.medication_service import get_medication_service
            medication_service = get_medication_service()
            medication_service.record_detection_result(
                medication_id=self.current_detection['medication_id'],
                detected=True,
                match_result=None,
                confidence=None,
                photo_path=str(photo_path)
            )
            await self._handle_verification_failed("No reference photo available")
            return
        
        reference_image = await self._fetch_reference_photo(reference_photo_url)
        
        if reference_image is None:
            print(f"❌ Failed to fetch reference photo")
            await self._handle_verification_failed("Could not fetch reference photo")
            return
        
        # Verify with OpenAI Vision
        match_result, confidence = await self._verify_with_openai_vision(frame, reference_image)
        
        # Record result
        from services.medication_service import get_medication_service
        medication_service = get_medication_service()
        medication_service.record_detection_result(
            medication_id=medication_id,
            detected=True,
            match_result=match_result,
            confidence=confidence,
            photo_path=str(photo_path)
        )
        
        # Provide feedback
        if match_result:
            await self._handle_verification_success()
        else:
            await self._handle_verification_failed("Medication does not match")
        
        self.current_detection['verification_complete'] = True
    
    async def _fetch_reference_photo(self, photo_url: str) -> Optional[np.ndarray]:
        """
        Fetch reference photo from Lambda API
        
        Args:
            photo_url: URL to reference photo
        
        Returns:
            numpy array of image (RGB format) or None if failed
        """
        try:
            print(f"📥 Fetching reference photo: {photo_url}")
            
            response = await asyncio.to_thread(requests.get, photo_url, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ Failed to fetch reference photo: {response.status_code}")
                return None
            
            # Decode image
            image_bytes = response.content
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                print(f"❌ Failed to decode reference photo")
                return None
            
            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            print(f"✅ Reference photo fetched successfully ({image_rgb.shape})")
            return image_rgb
            
        except Exception as e:
            print(f"❌ Error fetching reference photo: {e}")
            return None
    
    async def _verify_with_openai_vision(self, detected_image: np.ndarray, 
                                         reference_image: np.ndarray) -> Tuple[Optional[bool], Optional[float]]:
        """
        Verify medication using OpenAI Vision API
        
        Args:
            detected_image: Captured image with medication bottle (RGB numpy array)
            reference_image: Reference medication photo (RGB numpy array)
        
        Returns:
            Tuple of (match_result: bool or None, confidence: float or None)
        """
        if not self.openai_client:
            print("⚠️  OpenAI client not available, skipping verification")
            return None, None
        
        try:
            # Encode images to base64
            def encode_image(image: np.ndarray) -> str:
                # Convert RGB to BGR for cv2
                image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                # Encode to JPEG
                _, buffer = cv2.imencode('.jpg', image_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
                image_bytes = buffer.tobytes()
                return base64.b64encode(image_bytes).decode('utf-8')
            
            detected_base64 = encode_image(detected_image)
            reference_base64 = encode_image(reference_image)
            
            # Call OpenAI Vision API
            print(f"🤖 Sending images to OpenAI Vision for verification...")
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medication verification assistant. Compare the two images and determine if they show the same medication. Respond with ONLY a JSON object: {\"match\": true/false, \"confidence\": 0.0-1.0, \"reason\": \"brief explanation\"}"
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{reference_base64}",
                                    "detail": "low"
                                }
                            },
                            {
                                "type": "text",
                                "text": "This is the reference medication photo."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{detected_base64}",
                                    "detail": "low"
                                }
                            },
                            {
                                "type": "text",
                                "text": "Does this detected medication bottle match the reference? Respond with JSON only."
                            }
                        ]
                    }
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            print(f"📋 OpenAI response: {response_text}")
            
            # Try to extract JSON
            import json
            import re
            
            # Find JSON in response
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
                match_result = result.get('match', False)
                confidence = result.get('confidence', 0.0)
                reason = result.get('reason', '')
                
                print(f"✅ Verification result: match={match_result}, confidence={confidence:.2f}, reason={reason}")
                return match_result, confidence
            else:
                print(f"⚠️  Could not parse JSON from OpenAI response")
                return None, None
            
        except Exception as e:
            print(f"❌ Error verifying with OpenAI Vision: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    async def _handle_verification_success(self):
        """Handle successful medication verification"""
        from services.tts_service import get_tts_service
        from services.oled_display import get_oled_service
        import config
        
        tts = get_tts_service()
        oled = get_oled_service()
        
        # TTS + OLED feedback
        tts_task = asyncio.create_task(tts.speak_async(config.MEDICATION_TTS_MATCH))
        oled_task = asyncio.create_task(asyncio.to_thread(oled.show_message, config.MEDICATION_OLED_MATCH))
        
        await asyncio.gather(tts_task, oled_task)
        
        print(f"✅ Medication verified successfully!")
    
    async def _handle_verification_failed(self, reason: str):
        """Handle failed medication verification"""
        from services.tts_service import get_tts_service
        from services.oled_display import get_oled_service
        import config
        
        tts = get_tts_service()
        oled = get_oled_service()
        
        # TTS + OLED feedback
        tts_task = asyncio.create_task(tts.speak_async(config.MEDICATION_TTS_NO_MATCH))
        oled_task = asyncio.create_task(asyncio.to_thread(oled.show_message, config.MEDICATION_OLED_NO_MATCH))
        
        await asyncio.gather(tts_task, oled_task)
        
        print(f"❌ Medication verification failed: {reason}")
    
    async def _handle_no_detection(self):
        """Handle case where no medication bottle was detected in window"""
        from services.tts_service import get_tts_service
        from services.oled_display import get_oled_service
        import config
        
        tts = get_tts_service()
        oled = get_oled_service()
        
        # TTS + OLED feedback
        tts_task = asyncio.create_task(tts.speak_async(config.MEDICATION_TTS_NOT_DETECTED))
        oled_task = asyncio.create_task(asyncio.to_thread(oled.show_message, config.MEDICATION_OLED_NO_MATCH))
        
        await asyncio.gather(tts_task, oled_task)
        
        # Record detection result
        if self.current_detection:
            from services.medication_service import get_medication_service
            medication_service = get_medication_service()
            medication_service.record_detection_result(
                medication_id=self.current_detection['medication_id'],
                detected=False,
                match_result=None,
                confidence=None,
                photo_path=None
            )
        
        print(f"⚠️  No medication bottle detected in time window")


# Singleton accessor
_medication_detection_service: Optional[MedicationDetectionService] = None

def get_medication_detection_service() -> MedicationDetectionService:
    """Get the singleton medication detection service instance"""
    global _medication_detection_service
    if _medication_detection_service is None:
        _medication_detection_service = MedicationDetectionService()
    return _medication_detection_service

