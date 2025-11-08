#!/usr/bin/env python3
"""
Test picamera2 inside Docker container
This should be run INSIDE the Docker container
"""

import sys
import time

print("="*60)
print("DOCKER CAMERA TEST (picamera2)")
print("="*60)
print()

# Test 1: Import picamera2
print("1. Importing picamera2...")
try:
    from picamera2 import Picamera2
    print("   ✅ picamera2 imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import picamera2: {e}")
    print()
    print("   This means python3-picamera2 was not installed correctly.")
    sys.exit(1)

print()

# Test 2: Create camera object
print("2. Creating camera object...")
try:
    picam = Picamera2()
    print("   ✅ Camera object created")
except Exception as e:
    print(f"   ❌ Failed to create camera: {e}")
    print()
    print("   Possible issues:")
    print("   - Camera device not mapped in docker-compose.yml")
    print("   - Missing privileged: true in docker-compose.yml")
    print("   - Camera not enabled on Raspberry Pi")
    sys.exit(1)

print()

# Test 3: Get camera info
print("3. Getting camera info...")
try:
    info = picam.global_camera_info()
    print(f"   ✅ Camera info: {info}")
except Exception as e:
    print(f"   ❌ Failed to get camera info: {e}")
    sys.exit(1)

print()

# Test 4: Configure
print("4. Configuring camera...")
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

# Test 5: Start
print("5. Starting camera...")
try:
    picam.start()
    print("   ✅ Camera started")
    time.sleep(2)
except Exception as e:
    print(f"   ❌ Failed to start: {e}")
    picam.close()
    sys.exit(1)

print()

# Test 6: Capture
print("6. Capturing frame...")
try:
    frame = picam.capture_array()
    print(f"   ✅ Frame captured: {frame.shape}")
except Exception as e:
    print(f"   ❌ Failed to capture: {e}")
    picam.stop()
    picam.close()
    sys.exit(1)

print()

# Cleanup
print("7. Cleaning up...")
picam.stop()
picam.close()
print("   ✅ Camera closed")

print()
print("="*60)
print("✅ DOCKER CAMERA TEST PASSED!")
print("="*60)
print()
print("picamera2 is working correctly inside Docker!")
print()

