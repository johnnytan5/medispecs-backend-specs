#!/bin/bash
# Quick start script for Docker on Raspberry Pi

set -e

echo "=================================================="
echo "🐳 MediSpecs Docker Startup (Raspberry Pi)"
echo "=================================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo ""
    echo "Creating .env file..."
    cat > .env << 'EOF'
LAMBDA_API_URL=https://zqglpdheqk.execute-api.ap-southeast-1.amazonaws.com/staging
USER_ID=u_123
EOF
    echo "✅ .env file created with default values"
    echo ""
fi

# Check if camera is accessible
echo "Checking camera access..."
if [ ! -e "/dev/video0" ]; then
    echo "⚠️  WARNING: /dev/video0 not found!"
    echo "   Make sure camera is enabled: sudo raspi-config"
    echo "   Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Camera device /dev/video0 found"
fi
echo ""

# Check if I2C is accessible (for OLED)
if [ ! -e "/dev/i2c-1" ]; then
    echo "⚠️  WARNING: /dev/i2c-1 not found!"
    echo "   OLED display may not work. Enable I2C: sudo raspi-config"
else
    echo "✅ I2C device /dev/i2c-1 found"
fi
echo ""

# Stop any running containers
echo "Stopping any existing containers..."
docker-compose down
echo ""

# Build with no cache for fresh start
echo "Building Docker image (this may take 5-10 minutes)..."
docker-compose build --no-cache
echo ""

# Start services
echo "Starting services..."
docker-compose up -d
echo ""

echo "=================================================="
echo "✅ Docker containers started!"
echo "=================================================="
echo ""
echo "View logs:"
echo "  docker-compose logs -f"
echo ""
echo "Stop services:"
echo "  docker-compose down"
echo ""
echo "API should be available at:"
echo "  http://localhost:8000"
echo ""

