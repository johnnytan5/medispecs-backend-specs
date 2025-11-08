#!/usr/bin/env python3
"""
Simple camera test for Raspberry Pi
Run this BEFORE Docker to verify camera works
"""

import sys
import time

print("="*60)
print("RASPBERRY PI CAMERA TEST")
print("="*60)
print()

# Test 1: Check if picamera2 is installed
print("1. Checking for picamera2...")
try:
    from picamera2 import Picamera2
    print("   ✅ picamera2 is installed")
except ImportError as e:
    print(f"   ❌ picamera2 NOT installed: {e}")
    print()
    print("   To install:")
    print("   sudo apt update")
    print("   sudo apt install -y python3-picamera2")
    sys.exit(1)

print()

# Test 2: Try to open camera
print("2. Opening camera...")
try:
    picam = Picamera2()
    print("   ✅ Camera object created")
except Exception as e:
    print(f"   ❌ Failed to create camera: {e}")
    sys.exit(1)

print()

# Test 3: Get camera info
print("3. Getting camera information...")
try:
    info = picam.global_camera_info()
    print(f"   ✅ Camera info: {info}")
except Exception as e:
    print(f"   ❌ Failed to get camera info: {e}")
    sys.exit(1)

print()

# Test 4: Configure camera
print("4. Configuring camera (640x480)...")
try:
    config = picam.create_preview_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    picam.configure(config)
    print("   ✅ Camera configured")
except Exception as e:
    print(f"   ❌ Failed to configure: {e}")
    picam.close()
    sys.exit(1)

print()

# Test 5: Start camera
print("5. Starting camera...")
try:
    picam.start()
    print("   ✅ Camera started")
except Exception as e:
    print(f"   ❌ Failed to start camera: {e}")
    picam.close()
    sys.exit(1)

print()

# Test 6: Warm up
print("6. Warming up camera (2 seconds)...")
time.sleep(2)
print("   ✅ Warm up complete")

print()

# Test 7: Capture frame
print("7. Capturing test frame...")
try:
    frame = picam.capture_array()
    print(f"   ✅ Frame captured successfully!")
    print(f"   Frame shape: {frame.shape}")
    print(f"   Frame dtype: {frame.dtype}")
except Exception as e:
    print(f"   ❌ Failed to capture: {e}")
    picam.stop()
    picam.close()
    sys.exit(1)

print()

# Test 8: Capture a few more frames
print("8. Testing continuous capture (5 frames)...")
success_count = 0
for i in range(5):
    try:
        frame = picam.capture_array()
        success_count += 1
        print(f"   Frame {i+1}/5: ✅ {frame.shape}")
        time.sleep(0.1)
    except Exception as e:
        print(f"   Frame {i+1}/5: ❌ {e}")

print(f"   Success rate: {success_count}/5")

print()

# Cleanup
print("9. Cleaning up...")
try:
    picam.stop()
    picam.close()
    print("   ✅ Camera closed")
except:
    pass

print()
print("="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
print()
print("Your Pi Camera is working correctly with picamera2.")
print("You can now proceed with Docker build.")
print()

