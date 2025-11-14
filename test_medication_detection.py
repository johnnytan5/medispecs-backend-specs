"""
Raspberry Pi Standalone Inference - Minimal Dependencies
Just copy this file + model to Pi and run!

Uses picamera2 for Raspberry Pi camera, falls back to OpenCV for USB cameras.
"""

from ultralytics import YOLO
import cv2
import time
import sys
import os

# Try to import picamera2 (for Raspberry Pi)
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    print("⚠️  picamera2 not available, will use OpenCV instead")

# Get model path from command line or use default
MODEL_PATH = sys.argv[1] if len(sys.argv) > 1 else 'medication_model.pt'

if not os.path.exists(MODEL_PATH):
    print(f"❌ Model not found: {MODEL_PATH}")
    print(f"Usage: python {sys.argv[0]} <model_path>")
    print(f"Example: python {sys.argv[0]} medication_model.pt")
    sys.exit(1)

print("=" * 70)
print("🍓 Raspberry Pi Medication Detection")
print("=" * 70)

# Load model
print(f"\n📦 Loading model: {MODEL_PATH}")
model = YOLO(MODEL_PATH)
print("✅ Model loaded")

# Initialize camera
picam = None
cap = None
use_picamera = False

if PICAMERA2_AVAILABLE:
    try:
        print(f"\n📷 Attempting to open Pi Camera using picamera2...")
        picam = Picamera2()
        
        # Configure camera for 640x480 RGB
        config = picam.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        picam.configure(config)
        
        print(f"   Starting camera...")
        picam.start()
        
        # Give camera time to initialize
        print(f"   Waiting for camera to warm up...")
        time.sleep(2)
        
        # Test capture
        test_frame = picam.capture_array()
        print(f"   Test capture successful: {test_frame.shape}")
        
        use_picamera = True
        width, height = 640, 480
        print(f"✅ Pi Camera opened successfully (picamera2)")
        print(f"📹 Camera: {width}x{height}")
        
    except Exception as e:
        print(f"⚠️  Failed to open picamera2: {e}")
        print(f"   Falling back to OpenCV...")
        use_picamera = False

# Fallback to OpenCV (for USB cameras or if picamera2 fails)
if not use_picamera:
    print(f"\n📷 Opening camera using OpenCV (index: 0)")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Cannot open webcam!")
        sys.exit(1)
    
    # Set lower resolution for Pi performance
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"✅ Camera opened successfully (OpenCV)")
    print(f"📹 Camera: {width}x{height}")

print("\n🎯 Starting detection...")
print("   Press 'q' to quit")
print("=" * 70 + "\n")

frame_count = 0
fps_list = []
start_time = time.time()

try:
    while True:
        frame_start = time.time()
        
        # Get frame from appropriate camera source
        if use_picamera:
            # Capture frame from picamera2 (returns RGB)
            frame = picam.capture_array()
            # picamera2 already provides RGB, no conversion needed
        else:
            # Capture frame from OpenCV (returns BGR)
            ret, frame = cap.read()
            if not ret:
                break
            # Convert BGR to RGB for YOLO
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Run inference with Pi optimizations
        results = model.predict(
            frame,
            conf=0.05,          # Low threshold for your model
            verbose=False,
            device='cpu',       # CPU on Pi
            imgsz=320,          # Smaller = faster
            half=False,
            augment=False,
        )
        
        # Draw results (plot() returns RGB numpy array)
        annotated = results[0].plot()
        
        # Convert RGB to BGR for OpenCV display (cv2.imshow expects BGR)
        annotated = cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR)
        
        # Calculate FPS
        frame_time = time.time() - frame_start
        fps = 1.0 / frame_time if frame_time > 0 else 0
        fps_list.append(fps)
        
        if len(fps_list) > 30:
            fps_list.pop(0)
        
        avg_fps = sum(fps_list) / len(fps_list)
        
        # Display FPS
        cv2.putText(
            annotated,
            f"FPS: {avg_fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )
        
        # Display detection count
        num_det = len(results[0].boxes)
        if num_det > 0:
            confidences = [float(box.conf[0]) for box in results[0].boxes]
            max_conf = max(confidences)
            cv2.putText(
                annotated,
                f"Detections: {num_det} (max: {max_conf:.2f})",
                (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )
            print(f"💊 Detected {num_det} bottle(s) (max confidence: {max_conf:.3f})")
        
        cv2.imshow('Medication Detection', annotated)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        frame_count += 1

except KeyboardInterrupt:
    print("\n⏹️  Stopped")

finally:
    # Cleanup
    if use_picamera and picam:
        picam.stop()
        print("📷 Pi Camera stopped")
    elif cap:
        cap.release()
        print("📷 OpenCV camera released")
    
    cv2.destroyAllWindows()
    
    total_time = time.time() - start_time
    avg_fps = frame_count / total_time if total_time > 0 else 0
    
    print(f"\n📊 Processed {frame_count} frames in {total_time:.1f}s")
    print(f"   Average FPS: {avg_fps:.1f}")
    print("✅ Done!")

