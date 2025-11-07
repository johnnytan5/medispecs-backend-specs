"""
OLED Device Initialization for Raspberry Pi
This module initializes the OLED display hardware.
"""

def get_device():
    """
    Initialize and return the OLED device.
    This will only work on Raspberry Pi with OLED hardware connected via I2C.
    """
    try:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        
        # Initialize I2C interface
        # Default I2C bus is 1 on Raspberry Pi
        # Default I2C address is 0x3C (can be 0x3D on some displays)
        serial = i2c(port=1, address=0x3C)
        
        # Initialize SSD1306 OLED display (128x64 pixels)
        # Change to ssd1306_128x32 if you have a 128x32 display
        device = ssd1306(serial)
        
        return device
        
    except ImportError as e:
        raise ImportError(
            "luma.oled library not installed. "
            "Install it with: pip install luma.oled"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Failed to initialize OLED display: {e}. "
            "Make sure I2C is enabled and OLED is connected properly."
        ) from e


def get_device_128x32():
    """
    Initialize and return a 128x32 OLED device.
    Use this if you have a smaller 128x32 display.
    """
    try:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        
        serial = i2c(port=1, address=0x3C)
        device = ssd1306(serial, width=128, height=32)
        
        return device
        
    except ImportError as e:
        raise ImportError(
            "luma.oled library not installed. "
            "Install it with: pip install luma.oled"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Failed to initialize OLED display: {e}. "
            "Make sure I2C is enabled and OLED is connected properly."
        ) from e

