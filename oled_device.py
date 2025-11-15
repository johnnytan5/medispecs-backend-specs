"""
OLED Device Initialization for Raspberry Pi
This module initializes the OLED display hardware with retry logic.
"""

import time
from typing import Optional


def get_device(max_retries: int = 3, retry_delay: float = 0.5, timeout: float = 2.0):
    """
    Initialize and return the OLED device with retry logic.
    This will only work on Raspberry Pi with OLED hardware connected via I2C.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Delay between retries in seconds (default: 0.5)
        timeout: I2C connection timeout in seconds (default: 2.0)
    
    Returns:
        OLED device instance
        
    Raises:
        ImportError: If luma.oled library is not installed
        RuntimeError: If initialization fails after all retries
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306
            
            # Initialize I2C interface with timeout
            # Default I2C bus is 1 on Raspberry Pi
            # Default I2C address is 0x3C (can be 0x3D on some displays)
            # Try both common addresses
            addresses_to_try = [0x3C, 0x3D]
            
            for address in addresses_to_try:
                try:
                    # Create I2C interface with timeout
                    serial = i2c(port=1, address=address)
                    
                    # Initialize SSD1306 OLED display (128x64 pixels)
                    # Change to ssd1306_128x32 if you have a 128x32 display
                    device = ssd1306(serial)
                    
                    # Test connection by clearing display
                    device.clear()
                    
                    if attempt > 0:
                        print(f"✅ OLED display initialized successfully on attempt {attempt + 1} (address: 0x{address:02X})")
                    
                    return device
                    
                except Exception as addr_error:
                    if address == addresses_to_try[-1]:
                        # Last address failed, raise the error
                        raise addr_error
                    # Try next address
                    continue
            
        except ImportError as e:
            raise ImportError(
                "luma.oled library not installed. "
                "Install it with: pip install luma.oled"
            ) from e
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                print(f"⚠️  OLED initialization attempt {attempt + 1}/{max_retries} failed: {e}")
                print(f"   Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                # Last attempt failed
                print(f"❌ OLED initialization failed after {max_retries} attempts")
                raise RuntimeError(
                    f"Failed to initialize OLED display after {max_retries} attempts: {last_error}. "
                    "Make sure I2C is enabled and OLED is connected properly."
                ) from last_error
    
    # Should never reach here, but just in case
    raise RuntimeError(f"Failed to initialize OLED display: {last_error}")


def get_device_128x32(max_retries: int = 3, retry_delay: float = 0.5):
    """
    Initialize and return a 128x32 OLED device with retry logic.
    Use this if you have a smaller 128x32 display.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Delay between retries in seconds (default: 0.5)
    
    Returns:
        OLED device instance (128x32)
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306
            
            # Try both common addresses
            addresses_to_try = [0x3C, 0x3D]
            
            for address in addresses_to_try:
                try:
                    serial = i2c(port=1, address=address)
                    device = ssd1306(serial, width=128, height=32)
                    
                    # Test connection
                    device.clear()
                    
                    if attempt > 0:
                        print(f"✅ OLED display (128x32) initialized successfully on attempt {attempt + 1} (address: 0x{address:02X})")
                    
                    return device
                    
                except Exception as addr_error:
                    if address == addresses_to_try[-1]:
                        raise addr_error
                    continue
            
        except ImportError as e:
            raise ImportError(
                "luma.oled library not installed. "
                "Install it with: pip install luma.oled"
            ) from e
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"⚠️  OLED (128x32) initialization attempt {attempt + 1}/{max_retries} failed: {e}")
                print(f"   Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                raise RuntimeError(
                    f"Failed to initialize OLED display (128x32) after {max_retries} attempts: {last_error}. "
                    "Make sure I2C is enabled and OLED is connected properly."
                ) from last_error
    
    raise RuntimeError(f"Failed to initialize OLED display (128x32): {last_error}")

