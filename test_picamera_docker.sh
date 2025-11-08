#!/bin/bash
# Test if picamera2 works inside Docker container

echo "=========================================="
echo "Testing Pi Camera in Docker Container"
echo "=========================================="
echo ""

# Check if running in Docker
if [ -f /.dockerenv ]; then
    echo "✅ Running inside Docker container"
else
    echo "⚠️  Not running in Docker"
fi
echo ""

# Check for camera devices
echo "Camera devices available:"
ls -l /dev/video* /dev/vchiq /dev/vcsm-cma 2>/dev/null || echo "No camera devices found"
echo ""

# Check video group
echo "Video group membership:"
groups
echo ""

# Test with Python
echo "Testing picamera2 import..."
python3 << 'EOF'
import sys

try:
    from picamera2 import Picamera2
    print("✅ picamera2 imported successfully")
    
    print("\nAttempting to open camera...")
    picam = Picamera2()
    
    print(f"Camera info: {picam.global_camera_info()}")
    
    print("\nConfiguring camera...")
    config = picam.create_preview_configuration(main={"size": (640, 480)})
    picam.configure(config)
    
    print("Starting camera...")
    picam.start()
    
    import time
    time.sleep(2)
    
    print("Capturing test frame...")
    frame = picam.capture_array()
    print(f"✅ Success! Frame shape: {frame.shape}")
    
    picam.stop()
    
except ImportError as e:
    print(f"❌ picamera2 not available: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

echo ""
echo "=========================================="
echo "Test complete"
echo "=========================================="

