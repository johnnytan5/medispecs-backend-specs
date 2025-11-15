"""
Button Service - Simple Button Press Detection
Detects button presses on GPIO pin and logs to console
Uses gpiozero (more reliable than RPi.GPIO)
"""
import asyncio
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any

# Try to import gpiozero
try:
    from gpiozero import Button
    GPIOZERO_AVAILABLE = True
except ImportError:
    GPIOZERO_AVAILABLE = False
    print("⚠️  gpiozero not installed. Button detection will be disabled.")
    print("   Install with: pip install gpiozero")


class ButtonService:
    """
    Simple button press detection service
    
    Features:
    - Detects button presses on GPIO pin
    - Logs presses to console with timestamp
    - Built-in debouncing via gpiozero
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
        self.pull_up = True  # Pull-up resistor (button connects to GND when pressed)
        self.bounce_time = 0.05  # 50ms bounce time (debounce)
        
        # gpiozero Button object
        self.button: Optional[Button] = None
        
        # State tracking
        self.press_count = 0
        self.button_callback: Optional[Callable] = None
    
    def initialize(self, button_pin: int = 18, pull_up: bool = True, bounce_time: float = 0.05) -> bool:
        """
        Initialize button service with configuration
        
        Args:
            button_pin: GPIO pin number (BCM numbering, default: 18)
            pull_up: True for pull-up (button to GND), False for pull-down (button to 3.3V)
            bounce_time: Bounce time in seconds (default: 0.05 = 50ms)
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if not GPIOZERO_AVAILABLE:
            print("❌ Button service dependencies not available")
            return False
        
        try:
            self.button_pin = button_pin
            self.pull_up = pull_up
            self.bounce_time = bounce_time
            
            print(f"✅ Button service initialized")
            print(f"   GPIO Pin: {self.button_pin} (BCM)")
            print(f"   Pull-up: {pull_up}")
            print(f"   Bounce time: {bounce_time*1000:.0f}ms")
            
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
        if not GPIOZERO_AVAILABLE:
            print("⏸️  Button detection disabled (gpiozero not available)")
            return
        
        if self.is_running:
            print("⚠️  Button detection is already running")
            return
        
        # Create gpiozero Button object
        try:
            self.button = Button(
                self.button_pin,
                pull_up=self.pull_up,
                bounce_time=self.bounce_time
            )
            
            # Set up button press handler
            self.button.when_pressed = self._on_button_pressed
            
            print(f"✅ GPIO pin {self.button_pin} configured for button input")
            print(f"🔘 Button detection started on GPIO {self.button_pin}")
            
            self.is_running = True
            
        except Exception as e:
            print(f"❌ Failed to setup GPIO: {e}")
            print(f"   Make sure:")
            print(f"   1. GPIO pin {self.button_pin} is not in use by another process")
            print(f"   2. You have permission to access GPIO (may need sudo or gpio group)")
            print(f"   3. Button is wired correctly")
            return
    
    async def stop(self):
        """Stop button detection service"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Close button
        if self.button:
            try:
                self.button.close()
                print(f"🔘 GPIO pin {self.button_pin} closed")
            except:
                pass
            self.button = None
        
        print("🛑 Button detection stopped")
    
    def _on_button_pressed(self):
        """Handle button press event (called by gpiozero)"""
        # This runs in a separate thread from gpiozero
        # We need to schedule the async handler
        if self.is_running:
            # Create task to handle async callback
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._handle_button_press())
                else:
                    loop.run_until_complete(self._handle_button_press())
            except RuntimeError:
                # If no event loop, create a new one
                asyncio.run(self._handle_button_press())
    
    async def _handle_button_press(self):
        """Handle button press event (async)"""
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
                import traceback
                traceback.print_exc()
    
    def get_status(self) -> Dict[str, Any]:
        """Get button service status"""
        return {
            'is_running': self.is_running,
            'button_pin': self.button_pin,
            'press_count': self.press_count,
        }


# Singleton accessor
_button_service: Optional[ButtonService] = None

def get_button_service() -> ButtonService:
    """Get the singleton button service instance"""
    global _button_service
    if _button_service is None:
        _button_service = ButtonService()
    return _button_service
