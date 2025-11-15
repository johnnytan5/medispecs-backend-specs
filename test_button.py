#!/usr/bin/env python3
"""
Simple Button Test Script
Tests button detection on Raspberry Pi

Usage:
    python test_button.py [GPIO_PIN]

Example:
    python test_button.py 18
"""
import asyncio
import sys
from services.button_service import get_button_service

async def main():
    # Get GPIO pin from command line or use default
    button_pin = int(sys.argv[1]) if len(sys.argv) > 1 else 18
    
    print("=" * 60)
    print("🔘 Button Detection Test")
    print("=" * 60)
    print(f"GPIO Pin: {button_pin} (BCM numbering)")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    # Get button service
    button_service = get_button_service()
    
    # Initialize
    if not button_service.initialize(button_pin=button_pin, pull_up=True, bounce_time=0.05):
        print("❌ Failed to initialize button service")
        return 1
    
    # Start monitoring
    await button_service.start()
    
    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping button detection...")
    finally:
        await button_service.stop()
        print("✅ Test completed")
    
    return 0

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

