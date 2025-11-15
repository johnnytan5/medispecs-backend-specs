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
        
        # Event loop reference (for async callbacks from gpiozero thread)
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
    
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
        
        # Store reference to current event loop (for async callbacks from gpiozero thread)
        try:
            self.event_loop = asyncio.get_running_loop()
            print(f"✅ Event loop reference stored for async callbacks")
            print(f"   Event loop: {self.event_loop}")
            print(f"   Loop running: {self.event_loop.is_running()}")
        except RuntimeError as e:
            print(f"⚠️  Could not get event loop - async callbacks may not work: {e}")
            # Try alternative method
            try:
                self.event_loop = asyncio.get_event_loop()
                print(f"✅ Got event loop via get_event_loop()")
            except:
                self.event_loop = None
        
        # Create gpiozero Button object
        try:
            self.button = Button(
                self.button_pin,
                pull_up=self.pull_up,
                bounce_time=self.bounce_time
            )
            
            # Set up button press handler
            self.button.when_pressed = self._on_button_pressed
            
            # Test button state
            current_state = "HIGH" if self.button.is_pressed else "LOW"
            print(f"✅ GPIO pin {self.button_pin} configured for button input")
            print(f"   Current button state: {current_state}")
            print(f"   Expected: HIGH (not pressed) with pull_up=True")
            print(f"🔘 Button detection started on GPIO {self.button_pin}")
            print(f"   Press the button to test...")
            
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
        # Always log synchronously first (works from any thread)
        if self.is_running:
            self._handle_button_press_sync()
            
            # Then try to call async callback if set
            if self.button_callback:
                try:
                    # Check if callback is async
                    if asyncio.iscoroutinefunction(self.button_callback):
                        # Use stored event loop reference
                        if self.event_loop:
                            try:
                                if self.event_loop.is_running():
                                    # Schedule async callback in the main event loop
                                    print(f"📞 Scheduling async callback in event loop...")
                                    future = asyncio.run_coroutine_threadsafe(self.button_callback(), self.event_loop)
                                    print(f"✅ Async callback scheduled successfully")
                                else:
                                    print("⚠️  Event loop exists but is not running")
                                    print(f"   Attempting to run callback directly...")
                                    self.event_loop.run_until_complete(self.button_callback())
                            except Exception as e:
                                print(f"⚠️  Error scheduling async callback: {e}")
                                import traceback
                                traceback.print_exc()
                        else:
                            print("⚠️  Cannot call async callback (event loop not stored)")
                            print(f"   Event loop reference: {self.event_loop}")
                    else:
                        # Sync callback, call directly
                        self.button_callback()
                except Exception as e:
                    print(f"⚠️  Button callback error: {e}")
                    import traceback
                    traceback.print_exc()
    
    def _handle_button_press_sync(self):
        """Handle button press event (synchronous fallback)"""
        self.press_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Log to console (force flush to ensure it appears immediately)
        print(f"\n{'='*60}", flush=True)
        print(f"🔘 BUTTON PRESSED!", flush=True)
        print(f"   Timestamp: {timestamp}", flush=True)
        print(f"   GPIO Pin: {self.button_pin}", flush=True)
        print(f"   Total Presses: {self.press_count}", flush=True)
        print(f"{'='*60}\n", flush=True)
        
        # Call sync callback if set
        if self.button_callback and not asyncio.iscoroutinefunction(self.button_callback):
            try:
                self.button_callback()
            except Exception as e:
                print(f"⚠️  Button callback error: {e}")
                import traceback
                traceback.print_exc()
    
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
