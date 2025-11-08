#!/bin/bash
# Camera diagnostic script for Raspberry Pi

echo "========================================================"
echo "CAMERA DIAGNOSTICS - Raspberry Pi"
echo "========================================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo "⚠️  Running as root"
else
   echo "ℹ️  Running as user: $(whoami)"
fi
echo ""

# 1. Check for video devices
echo "1. Checking for video devices..."
echo "----------------------------------------"
if ls /dev/video* 2>/dev/null; then
    echo "✅ Video devices found"
    ls -l /dev/video*
else
    echo "❌ No video devices found"
    echo "   Solution: Enable camera in raspi-config"
fi
echo ""

# 2. Check camera module
echo "2. Checking Pi Camera Module..."
echo "----------------------------------------"
if vcgencmd get_camera 2>/dev/null; then
    echo "✅ Camera command available"
else
    echo "⚠️  vcgencmd not available or camera not detected"
fi
echo ""

# 3. Check for USB cameras
echo "3. Checking USB cameras..."
echo "----------------------------------------"
lsusb | grep -i camera || lsusb | grep -i webcam || echo "No USB cameras detected"
echo ""

# 4. Check v4l2 driver
echo "4. Checking v4l2 driver..."
echo "----------------------------------------"
if lsmod | grep -q "bcm2835-v4l2"; then
    echo "✅ bcm2835-v4l2 driver loaded"
else
    echo "❌ bcm2835-v4l2 driver NOT loaded"
    echo "   Solution: sudo modprobe bcm2835-v4l2"
fi
echo ""

# 5. Check if v4l-utils is installed
echo "5. Checking v4l-utils..."
echo "----------------------------------------"
if command -v v4l2-ctl &> /dev/null; then
    echo "✅ v4l-utils installed"
    echo ""
    echo "Camera capabilities:"
    v4l2-ctl --list-devices 2>/dev/null || echo "Cannot list devices"
else
    echo "❌ v4l-utils not installed"
    echo "   Solution: sudo apt-get install v4l-utils"
fi
echo ""

# 6. Check permissions
echo "6. Checking permissions..."
echo "----------------------------------------"
if [ -e /dev/video0 ]; then
    PERMS=$(ls -l /dev/video0)
    echo "$PERMS"
    
    if [ -r /dev/video0 ] && [ -w /dev/video0 ]; then
        echo "✅ Current user has read/write access"
    else
        echo "❌ Current user does NOT have access"
        echo "   Solution: sudo chmod 666 /dev/video0"
        echo "   Or add user to video group: sudo usermod -aG video $USER"
    fi
else
    echo "❌ /dev/video0 does not exist"
fi
echo ""

# 7. Check if camera is in use
echo "7. Checking if camera is in use..."
echo "----------------------------------------"
if command -v fuser &> /dev/null; then
    if [ -e /dev/video0 ]; then
        PROCS=$(sudo fuser /dev/video0 2>/dev/null)
        if [ -z "$PROCS" ]; then
            echo "✅ Camera is not in use"
        else
            echo "⚠️  Camera is being used by process(es): $PROCS"
        fi
    fi
else
    echo "⚠️  fuser command not available"
fi
echo ""

# 8. Try to capture a test frame
echo "8. Testing camera capture..."
echo "----------------------------------------"
if command -v python3 &> /dev/null; then
    python3 << 'EOF'
import cv2
import sys

print("Attempting to open camera...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Failed to open camera")
    sys.exit(1)

print("✅ Camera opened successfully")

ret, frame = cap.read()
if ret:
    print(f"✅ Frame captured: {frame.shape}")
else:
    print("❌ Failed to read frame")
    
cap.release()
EOF
else
    echo "⚠️  Python3 not available"
fi
echo ""

echo "========================================================"
echo "DIAGNOSTIC COMPLETE"
echo "========================================================"
echo ""
echo "Common Solutions:"
echo ""
echo "For Pi Camera Module:"
echo "  1. sudo raspi-config → Interface Options → Legacy Camera → Enable"
echo "  2. sudo modprobe bcm2835-v4l2"
echo "  3. echo 'bcm2835-v4l2' | sudo tee -a /etc/modules"
echo "  4. sudo reboot"
echo ""
echo "For USB Camera:"
echo "  1. Check USB connection"
echo "  2. sudo chmod 666 /dev/video0"
echo ""
echo "For Docker:"
echo "  1. Make sure /dev/video0 exists on host"
echo "  2. Check docker-compose.yml has correct device mapping"
echo "  3. Restart container: docker-compose restart"
echo ""

