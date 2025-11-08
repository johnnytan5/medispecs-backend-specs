#!/bin/bash
# Debug camera inside Docker container

echo "========================================"
echo "DOCKER CAMERA DEBUG"
echo "========================================"
echo ""

# Make sure container is running
if ! docker ps | grep -q medispecs-api; then
    echo "❌ Container is not running!"
    echo "Start it with: docker-compose up -d"
    exit 1
fi

echo "✅ Container is running"
echo ""

# Check Python version
echo "1. Python version:"
docker exec medispecs-api python3 --version
echo ""

# Check if picamera2 is installed
echo "2. Checking picamera2 installation:"
docker exec medispecs-api python3 -c "
try:
    import picamera2
    print('✅ picamera2 is installed')
    print(f'   Version: {picamera2.__version__ if hasattr(picamera2, \"__version__\") else \"unknown\"}')
except ImportError as e:
    print(f'❌ picamera2 NOT installed: {e}')
"
echo ""

# Check camera devices inside container
echo "3. Camera devices inside container:"
docker exec medispecs-api ls -l /dev/video* /dev/vchiq 2>/dev/null || echo "❌ No camera devices found"
echo ""

# Check libcap-dev
echo "4. Checking libcap library:"
docker exec medispecs-api dpkg -l | grep libcap || echo "❌ libcap not found"
echo ""

# Try to import and test picamera2
echo "5. Testing picamera2 inside container:"
docker exec medispecs-api python3 << 'EOF'
import sys
print("Attempting to import picamera2...")
try:
    from picamera2 import Picamera2
    print("✅ Import successful")
    
    print("\nAttempting to create camera object...")
    picam = Picamera2()
    print(f"✅ Camera object created")
    print(f"   Camera info: {picam.global_camera_info()}")
    
    print("\nConfiguring camera...")
    config = picam.create_preview_configuration(main={"size": (640, 480)})
    picam.configure(config)
    print("✅ Configured")
    
    print("\nStarting camera...")
    picam.start()
    print("✅ Started")
    
    import time
    time.sleep(2)
    
    print("\nCapturing frame...")
    frame = picam.capture_array()
    print(f"✅ SUCCESS! Frame shape: {frame.shape}")
    
    picam.stop()
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

echo ""
echo "========================================"
echo "DEBUG COMPLETE"
echo "========================================"

