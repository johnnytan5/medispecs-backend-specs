"""
OLED Display Service for MediSpecs
Handles displaying reminder messages on OLED screen
"""

from time import sleep
from PIL import Image, ImageDraw, ImageFont
import textwrap
from typing import Optional


class OLEDDisplayService:
    """Service for displaying messages on OLED screen"""
    
    def __init__(self, device=None):
        """
        Initialize OLED display service
        
        Args:
            device: OLED device instance. If None, will try to initialize.
        """
        self.device = device
        self._initialized = False
        
        if device is None:
            try:
                from demo_opts import get_device
                self.device = get_device()
                self._initialized = True
                print("✓ OLED display initialized")
            except Exception as e:
                print(f"⚠️  OLED display not available: {e}")
                self._initialized = False
        else:
            self._initialized = True
    
    @property
    def is_available(self) -> bool:
        """Check if OLED display is available"""
        return self._initialized and self.device is not None
    
    def get_text_size(self, draw, text, font):
        """Get text size compatible with both old and new Pillow versions."""
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            return width, height
        except AttributeError:
            return draw.textsize(text, font=font)
    
    def get_preferred_font(self, size=14):
        """Return a PIL ImageFont: try common TTFs, fallback to default."""
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
        return ImageFont.load_default()
    
    def blink_display(self, image, blinks=5, on_time=0.3, off_time=0.3):
        """Create a blinking effect by alternating between image and blank screen."""
        if not self.is_available:
            return
        
        blank = Image.new("1", (self.device.width, self.device.height))
        
        for _ in range(blinks):
            self.device.display(image)
            sleep(on_time)
            self.device.display(blank)
            sleep(off_time)
        
        self.device.display(image)
    
    def show_message(self, message, font=None, should_blink=True, display_time=10):
        """Display a centered message on the OLED screen with optional blinking."""
        if not self.is_available:
            print(f"OLED not available. Would display: {message}")
            return
        
        width = self.device.width
        height = self.device.height
        
        image = Image.new("1", (width, height))
        draw = ImageDraw.Draw(image)
        if font is None:
            font = self.get_preferred_font()
        
        text_width, text_height = self.get_text_size(draw, message, font)
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), message, font=font, fill=255)
        blank = Image.new("1", (width, height))
        
        if should_blink:
            self.blink_display(image)
        else:
            self.device.display(image)
        
        sleep(display_time)
        try:
            self.device.clear()
        except Exception:
            self.device.display(blank)
    
    def display_wrapped_message(self, message, max_chars_per_line=16, font=None, 
                               should_blink=True, display_time=10):
        """Wrap the message into multiple centered lines and display it."""
        if not self.is_available:
            print(f"OLED not available. Would display: {message}")
            return
        
        width = self.device.width
        height = self.device.height
        image = Image.new("1", (width, height))
        draw = ImageDraw.Draw(image)
        if font is None:
            font = self.get_preferred_font()
        
        lines = textwrap.wrap(message, width=max_chars_per_line) or [""]
        sizes = [self.get_text_size(draw, line, font) for line in lines]
        total_height = sum(h for _, h in sizes)
        y = max((height - total_height) // 2, 0)
        
        for (line, (w, h)) in zip(lines, sizes):
            x = max((width - w) // 2, 0)
            draw.text((x, y), line, font=font, fill=255)
            y += int(h * 1.2)
        
        blank = Image.new("1", (width, height))
        
        if should_blink:
            self.blink_display(image)
        else:
            self.device.display(image)
        
        sleep(display_time)
        try:
            self.device.clear()
        except Exception:
            self.device.display(blank)
    
    def display_scrolling_message(self, message, pause=1.0, step=1, delay=0.03, font=None):
        """Scroll the message upwards across the display."""
        if not self.is_available:
            print(f"OLED not available. Would display: {message}")
            return
        
        width = self.device.width
        height = self.device.height
        line_spacing = 1.2
        
        if font is None:
            font = self.get_preferred_font()
        
        tmp_img = Image.new("1", (1, 1))
        tmp_draw = ImageDraw.Draw(tmp_img)
        
        avg_w, _ = self.get_text_size(tmp_draw, "A", font)
        max_chars_per_line = max(1, width // max(1, avg_w))
        
        lines = textwrap.wrap(message, width=max_chars_per_line) or [""]
        sizes = [self.get_text_size(tmp_draw, line, font) for line in lines]
        
        total_text_height = int(sum(h * line_spacing for _, h in sizes))
        
        if total_text_height <= height:
            self.display_wrapped_message(message, max_chars_per_line=max_chars_per_line, font=font)
            return
        
        draw_start_y = height // 2
        full = Image.new("1", (width, 5000))
        draw = ImageDraw.Draw(full)
        
        y = draw_start_y
        for line in lines:
            w, h = self.get_text_size(draw, line, font)
            x = max((width - w) // 2, 0)
            draw.text((x, y), line, font=font, fill=255)
            y += int(h * 1.2)
        
        drawn_text_height = y - draw_start_y
        max_line_h = 0
        if sizes:
            max_line_h = max(int(h * line_spacing) for _, h in sizes)
        bottom_padding = height + max_line_h
        full_height = draw_start_y + drawn_text_height + bottom_padding
        full = full.crop((0, 0, width, full_height))
        
        max_offset = full_height - height
        offset = 0
        try:
            while offset <= max_offset:
                frame = full.crop((0, offset, width, offset + height))
                self.device.display(frame)
                offset += step
                sleep(delay)
        except KeyboardInterrupt:
            return
        
        sleep(pause)
        try:
            self.device.clear()
        except Exception:
            blank = Image.new("1", (width, height))
            self.device.display(blank)
    
    def display_reminder(self, message, font_size=14, should_blink=True, display_time=10):
        """
        Display a reminder message on OLED.
        Automatically chooses the best display mode based on message length.
        
        Args:
            message: The reminder message to display
            font_size: Font size to use (default: 14)
            should_blink: Whether to blink the message (default: True)
            display_time: How long to show the message in seconds (default: 10)
        """
        if not self.is_available:
            print(f"🔔 OLED not available. Reminder: {message}")
            return
        
        if message is None:
            message = ""
        
        try:
            self.device.clear()
        except Exception:
            blank = Image.new("1", (self.device.width, self.device.height))
            self.device.display(blank)
        
        font = self.get_preferred_font(size=font_size)
        
        tmp_img = Image.new("1", (1, 1))
        tmp_draw = ImageDraw.Draw(tmp_img)
        
        # Check if single line fits
        text_w, text_h = self.get_text_size(tmp_draw, message, font)
        if text_w <= self.device.width and text_h <= self.device.height:
            self.show_message(message, font=font, should_blink=should_blink, display_time=display_time)
            return
        
        # Check if wrapped text fits
        avg_w, _ = self.get_text_size(tmp_draw, "A", font)
        max_chars_per_line = max(1, self.device.width // max(1, avg_w))
        lines = textwrap.wrap(message, width=max_chars_per_line) or [""]
        sizes = [self.get_text_size(tmp_draw, line, font) for line in lines]
        total_h = sum(h for _, h in sizes)
        
        if total_h <= self.device.height:
            self.display_wrapped_message(message, max_chars_per_line=max_chars_per_line,
                                        font=font, should_blink=should_blink, 
                                        display_time=display_time)
        else:
            self.display_scrolling_message(message, font=font)
    
    def clear_display(self):
        """Clear the OLED display"""
        if not self.is_available:
            return
        
        try:
            self.device.clear()
        except Exception:
            blank = Image.new("1", (self.device.width, self.device.height))
            self.device.display(blank)


# Global instance
_oled_service: Optional[OLEDDisplayService] = None


def get_oled_service() -> OLEDDisplayService:
    """Get the global OLED display service instance"""
    global _oled_service
    if _oled_service is None:
        _oled_service = OLEDDisplayService()
    return _oled_service

