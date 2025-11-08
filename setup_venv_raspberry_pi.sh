#!/bin/bash
# Setup script for Raspberry Pi virtual environment
# This links system-wide picamera2 to avoid installation issues

set -e

echo "=================================================="
echo "Raspberry Pi Virtual Environment Setup"
echo "=================================================="
echo ""

# Check if running on Raspberry Pi
if [[ ! -f /proc/device-tree/model ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠️  Warning: This script is designed for Raspberry Pi OS"
    echo "   Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        exit 1
    fi
fi

# Install system dependencies
echo "1. Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-picamera2 \
    python3-numpy \
    python3-pil \
    libcap-dev \
    python3-dev \
    gcc \
    g++

echo "✅ System dependencies installed"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "2. Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "2. Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "3. Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Link system packages to venv
echo "4. Linking system packages to venv..."
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
VENV_SITE_PACKAGES="venv/lib/python${PYTHON_VERSION}/site-packages"

# Create path file to include system packages
echo "/usr/lib/python3/dist-packages" > "${VENV_SITE_PACKAGES}/system_packages.pth"
echo "✅ System packages linked"
echo ""

# Verify picamera2 is accessible
echo "5. Verifying picamera2 access..."
python3 -c "from picamera2 import Picamera2; print('✅ picamera2 is accessible')" 2>/dev/null || {
    echo "❌ Failed to import picamera2"
    echo "   Check that python3-picamera2 is installed"
    exit 1
}
echo ""

# Install Python dependencies
echo "6. Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Python dependencies installed"
echo ""

echo "=================================================="
echo "✅ Setup complete!"
echo "=================================================="
echo ""
echo "To activate the environment:"
echo "  source venv/bin/activate"
echo ""
echo "To run the server:"
echo "  uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
echo ""

