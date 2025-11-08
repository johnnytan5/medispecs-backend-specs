#!/usr/bin/env python3
"""
Simple camera test to verify camera and YOLO are working
Run this standalone to test before integrating with FastAPI
"""

import cv2
from ultralytics import YOLO
import time

def test_camera():
    """Test if camera is accessible"""
    print("📷 Testing camera access...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Failed to open camera")
        print("   Make sure:")
        print("   - Camera is not being used by another app")
        print("   - Terminal has camera permissions (System Settings → Privacy)")
        return False
    
    print("✅ Camera opened successfully")
    
    # Try to read a frame
    ret, frame = cap.read()
    if ret:
        print(f"✅ Frame captured: {frame.shape}")
    else:
        print("❌ Failed to capture frame")
        cap.release()
        return False
    
    cap.release()
    return True


def test_yolo():
    """Test if YOLO model loads and works"""
    print("\n🔍 Testing YOLO model...")
    
    try:
        model = YOLO("yolov8n.pt")
        print("✅ YOLO model loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to load YOLO model: {e}")
        return False


def test_face_detection_live(duration=10, confidence_threshold=0.65):
    """Test face detection live for a few seconds"""
    print(f"\n👤 Testing face detection for {duration} seconds...")
    print(f"   Confidence threshold: {confidence_threshold}")
    print("   Position yourself in front of the camera!")
    print()
    
    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Failed to open camera")
        return
    
    start_time = time.time()
    detection_count = 0
    
    try:
        while time.time() - start_time < duration:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Resize for faster processing
            frame_resized = cv2.resize(frame, (640, 480))
            
            # Run YOLO detection
            results = model(frame_resized, stream=True, verbose=False)
            
            # Collect valid detections
            valid_detections = []
            for result in results:
                for box in result.boxes:
                    cls = int(box.cls[0])
                    name = model.names[cls]
                    confidence = float(box.conf[0])
                    
                    if name == "person" and confidence >= confidence_threshold:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        box_area = (x2 - x1) * (y2 - y1)
                        valid_detections.append({
                            'confidence': confidence,
                            'box': (x1, y1, x2, y2),
                            'area': box_area
                        })
            
            if valid_detections:
                # Sort by confidence and take the best one
                valid_detections.sort(key=lambda d: d['confidence'], reverse=True)
                best = valid_detections[0]
                detection_count += 1
                x1, y1, x2, y2 = best['box']
                print(f"✅ Person detected! Confidence: {best['confidence']:.2f} | " +
                      f"Box: ({x1},{y1})-({x2},{y2}) | Area: {best['area']} px²")
                
                if len(valid_detections) > 1:
                    print(f"   (Filtered out {len(valid_detections)-1} other detection(s))")
            else:
                print("   No person detected (or below confidence threshold)")
            
            # Wait a bit (simulate 2Hz)
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    finally:
        cap.release()
    
    print(f"\n📊 Test complete!")
    print(f"   Total detections: {detection_count}")
    print(f"   Duration: {duration} seconds")


def main():
    """Run all tests"""
    print("="*60)
    print("🎯 FACE DETECTION TEST SUITE".center(60))
    print("="*60 + "\n")
    
    # Test 1: Camera
    if not test_camera():
        print("\n❌ Camera test failed. Fix camera issues before proceeding.")
        return
    
    # Test 2: YOLO
    if not test_yolo():
        print("\n❌ YOLO test failed. Install ultralytics: pip install ultralytics")
        return
    
    # Test 3: Live detection
    print("\n" + "="*60)
    input("Press ENTER to start live face detection test...")
    test_face_detection_live(duration=10)
    
    print("\n" + "="*60)
    print("✅ All tests complete!".center(60))
    print("="*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

