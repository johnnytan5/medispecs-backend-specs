"""
Button Service - Simple Button Press Detection
Detects button presses on GPIO pin and logs to console
"""
import asyncio
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any

# Try to import RPi.GPIO
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO not installed. Button detection will be disabled.")
    print("   Install with: pip install RPi.GPIO")


class ButtonService:
    """
    Simple button press detection service
    
    Features:
    - Detects button presses on GPIO pin
    - Logs presses to console with timestamp
    - Debouncing to prevent multiple triggers
    - Optional callback function for button press events
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.is_running = False
        self.button_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.button_pin = 18  # Default GPIO pin (BCM numbering)
        self.pull_up_down = GPIO.PUD_UP  # Pull-up resistor (button connects to GND when pressed)
        self.debounce_time = 0.05  # 50ms debounce time
        
        # State tracking
        self.last_press_time = 0
        self.press_count = 0
        self.button_callback: Optional[Callable] = None
    
    def initialize(self, button_pin: int = 18, pull_up: bool = True, debounce_ms: int = 50) -> bool:
        """
        Initialize button service with configuration
        
        Args:
            button_pin: GPIO pin number (BCM numbering, default: 18)
            pull_up: True for pull-up (button to GND), False for pull-down (button to 3.3V)
            debounce_ms: Debounce time in milliseconds (default: 50ms)
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if not GPIO_AVAILABLE:
            print("❌ Button service dependencies not available")
            return False
        
        try:
            self.button_pin = button_pin
            self.pull_up_down = GPIO.PUD_UP if pull_up else GPIO.PUD_DOWN
            self.debounce_time = debounce_ms / 1000.0  # Convert to seconds
            
            print(f"✅ Button service initialized")
            print(f"   GPIO Pin: {self.button_pin} (BCM)")
            print(f"   Pull-up: {pull_up}")
            print(f"   Debounce: {debounce_ms}ms")
            
            return True
            
        except Exception as e:
            print(f"❌ Button service initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def set_callback(self, callback: Optional[Callable]):
        """
        Set callback function to be called on button press
        
        Args:
            callback: Function to call when button is pressed (async or sync)
        """
        self.button_callback = callback
    
    async def start(self):
        """Start button detection service"""
        if not GPIO_AVAILABLE:
            print("⏸️  Button detection disabled (RPi.GPIO not available)")
            return
        
        if self.is_running:
            print("⚠️  Button detection is already running")
            return
        
        # Setup GPIO
        try:
            GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
            GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=self.pull_up_down)
            print(f"✅ GPIO pin {self.button_pin} configured for button input")
        except Exception as e:
            print(f"❌ Failed to setup GPIO: {e}")
            return
        
        self.is_running = True
        
        # Start button monitoring task
        self.button_task = asyncio.create_task(self._button_monitor_loop())
        
        print(f"🔘 Button detection started on GPIO {self.button_pin}")
    
    async def stop(self):
        """Stop button detection service"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel task
        if self.button_task:
            self.button_task.cancel()
            try:
                await self.button_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup GPIO
        try:
            GPIO.cleanup(self.button_pin)
            print(f"🔘 GPIO pin {self.button_pin} cleaned up")
        except:
            pass
        
        print("🛑 Button detection stopped")
    
    async def _button_monitor_loop(self):
        """Continuously monitor button state"""
        print("🔘 Button monitoring loop started")
        
        # Track previous state for edge detection
        last_state = None
        
        while self.is_running:
            try:
                # Read button state (non-blocking)
                current_state = await asyncio.to_thread(GPIO.input, self.button_pin)
                
                # Detect button press (falling edge for pull-up, rising edge for pull-down)
                if self.pull_up_down == GPIO.PUD_UP:
                    # Pull-up: button pressed when state goes LOW (0)
                    button_pressed = (current_state == GPIO.LOW)
                else:
                    # Pull-down: button pressed when state goes HIGH (1)
                    button_pressed = (current_state == GPIO.HIGH)
                
                # Detect edge (state change)
                if button_pressed and last_state != button_pressed:
                    # Debounce check
                    current_time = time.time()
                    if current_time - self.last_press_time > self.debounce_time:
                        # Button press detected!
                        await self._handle_button_press()
                        self.last_press_time = current_time
                
                last_state = button_pressed
                
                # Small delay to avoid CPU spinning
                await asyncio.sleep(0.01)  # 10ms polling interval
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Error in button monitor loop: {e}")
                await asyncio.sleep(0.1)
    
    async def _handle_button_press(self):
        """Handle button press event"""
        self.press_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Log to console
        print(f"\n{'='*60}")
        print(f"🔘 BUTTON PRESSED!")
        print(f"   Timestamp: {timestamp}")
        print(f"   GPIO Pin: {self.button_pin}")
        print(f"   Total Presses: {self.press_count}")
        print(f"{'='*60}\n")
        
        # Call callback if set
        if self.button_callback:
            try:
                if asyncio.iscoroutinefunction(self.button_callback):
                    await self.button_callback()
                else:
                    # Sync callback, run in thread
                    await asyncio.to_thread(self.button_callback)
            except Exception as e:
                print(f"⚠️  Button callback error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get button service status"""
        return {
            'is_running': self.is_running,
            'button_pin': self.button_pin,
            'press_count': self.press_count,
            'last_press_time': self.last_press_time if self.last_press_time > 0 else None
        }


# Singleton accessor
_button_service: Optional[ButtonService] = None

def get_button_service() -> ButtonService:
    """Get the singleton button service instance"""
    global _button_service
    if _button_service is None:
        _button_service = ButtonService()
    return _button_service

