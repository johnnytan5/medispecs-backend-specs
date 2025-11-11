"""
Accelerometer Service - MPU6050 Fall Detection for MediSpecs
Implements 3-stage fall detection algorithm for senior citizen safety
"""
import asyncio
import time
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import math

try:
    from mpu6050 import mpu6050
    MPU6050_AVAILABLE = True
except ImportError:
    MPU6050_AVAILABLE = False
    print("⚠️  mpu6050-raspberrypi not installed. Fall detection will be disabled.")


class FallDetectionState(Enum):
    """States in the fall detection state machine"""
    IDLE = "idle"  # Normal state, monitoring for free fall
    FREE_FALL = "free_fall"  # Free fall detected, waiting for impact
    IMPACT = "impact"  # Impact detected, monitoring for inactivity
    INACTIVITY = "inactivity"  # Inactivity detected, fall confirmed
    COOLDOWN = "cooldown"  # Cooldown period after fall detection


class AccelerometerService:
    """
    Service for MPU6050 accelerometer/gyroscope sensor
    Implements fall detection algorithm with 3 stages:
    1. Free Fall: Total acceleration < 0.4G (weightlessness)
    2. Impact: Total acceleration > 2.3G (collision with ground)
    3. Inactivity: Low movement for 5+ seconds (person not getting up)
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
        self.sensor: Optional[mpu6050] = None
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Configuration (will be set by initialize())
        self.i2c_address = 0x77
        self.sampling_rate = 50  # Hz
        self.sampling_interval = 0.02  # seconds (1/50 = 0.02)
        
        # Fall detection thresholds
        self.free_fall_threshold = 0.4  # G
        self.impact_threshold = 2.3  # G
        self.inactivity_duration = 5.0  # seconds
        self.cooldown_period = 20  # seconds
        
        # State machine
        self.state = FallDetectionState.IDLE
        self.state_start_time = time.time()
        
        # Detection tracking
        self.free_fall_start_time: Optional[float] = None
        self.impact_time: Optional[float] = None
        self.impact_magnitude: Optional[float] = None
        self.free_fall_magnitude: Optional[float] = None
        
        # Current readings
        self.current_accel = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.current_total_accel = 1.0  # Start at 1G (resting)
        
        # Emergency status (for polling endpoint)
        self.latest_fall_event: Optional[Dict[str, Any]] = None
        self.fall_acknowledged = False
        
        # Callbacks
        self.on_fall_detected = None  # Callback function when fall is detected
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize MPU6050 sensor with configuration
        
        Args:
            config: Dictionary with accelerometer settings from config.py
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            if not MPU6050_AVAILABLE:
                print("❌ MPU6050 library not available")
                return False
            
            # Load configuration
            self.i2c_address = config.get('ACCELEROMETER_I2C_ADDRESS', 0x77)
            self.sampling_rate = config.get('ACCELEROMETER_SAMPLING_RATE', 50)
            self.sampling_interval = 1.0 / self.sampling_rate
            
            self.free_fall_threshold = config.get('FALL_FREE_FALL_THRESHOLD', 0.4)
            self.impact_threshold = config.get('FALL_IMPACT_THRESHOLD', 2.3)
            self.inactivity_duration = config.get('FALL_INACTIVITY_DURATION', 5.0)
            self.cooldown_period = config.get('FALL_COOLDOWN_PERIOD', 20)
            
            # Initialize sensor
            print(f"🔧 Initializing MPU6050 at I2C address 0x{self.i2c_address:02X}...")
            self.sensor = mpu6050(self.i2c_address)
            
            # Test sensor by reading acceleration
            test_accel = self.sensor.get_accel_data()
            print(f"✅ MPU6050 initialized successfully")
            print(f"   Test reading: X={test_accel['x']:.2f} Y={test_accel['y']:.2f} Z={test_accel['z']:.2f} m/s²")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize MPU6050: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def start(self):
        """Start continuous fall detection monitoring"""
        if self.is_running:
            print("⚠️  Accelerometer service already running")
            return
        
        if not self.sensor:
            print("❌ Cannot start: MPU6050 not initialized")
            return
        
        self.is_running = True
        self.state = FallDetectionState.IDLE
        self.state_start_time = time.time()
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitor_continuously())
        print(f"👂 Fall detection started (sampling at {self.sampling_rate}Hz)")
    
    async def stop(self):
        """Stop fall detection monitoring"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        print("🛑 Fall detection stopped")
    
    async def _monitor_continuously(self):
        """
        Continuously monitor accelerometer and run fall detection algorithm
        Runs at configured sampling rate (default 50Hz)
        """
        print(f"📊 Monitoring accelerometer (thresholds: <{self.free_fall_threshold}G free fall, >{self.impact_threshold}G impact)")
        
        while self.is_running:
            try:
                # Read sensor data
                accel = await asyncio.to_thread(self.sensor.get_accel_data)
                
                # Convert m/s² to G (1G = 9.81 m/s²)
                self.current_accel = {
                    'x': accel['x'] / 9.81,
                    'y': accel['y'] / 9.81,
                    'z': accel['z'] / 9.81
                }
                
                # Calculate total acceleration (magnitude)
                self.current_total_accel = math.sqrt(
                    self.current_accel['x']**2 + 
                    self.current_accel['y']**2 + 
                    self.current_accel['z']**2
                )
                
                # Run state machine
                await self._process_fall_detection()
                
                # Sleep for sampling interval
                await asyncio.sleep(self.sampling_interval)
                
            except Exception as e:
                print(f"❌ Error reading accelerometer: {e}")
                await asyncio.sleep(1.0)  # Wait longer on error
    
    async def _process_fall_detection(self):
        """
        Fall detection state machine
        States: IDLE → FREE_FALL → IMPACT → INACTIVITY → (fall detected) → COOLDOWN → IDLE
        """
        current_time = time.time()
        time_in_state = current_time - self.state_start_time
        
        if self.state == FallDetectionState.IDLE:
            # Monitor for free fall (total acceleration drops near 0)
            if self.current_total_accel < self.free_fall_threshold:
                self._transition_to_state(FallDetectionState.FREE_FALL)
                self.free_fall_start_time = current_time
                self.free_fall_magnitude = self.current_total_accel
                print(f"🪂 Free fall detected! ({self.current_total_accel:.2f}G)")
        
        elif self.state == FallDetectionState.FREE_FALL:
            # Wait for impact (sudden spike in acceleration)
            if self.current_total_accel > self.impact_threshold:
                self._transition_to_state(FallDetectionState.IMPACT)
                self.impact_time = current_time
                self.impact_magnitude = self.current_total_accel
                print(f"💥 Impact detected! ({self.current_total_accel:.2f}G)")
            
            # Timeout if no impact within 1 second (probably not a fall)
            elif time_in_state > 1.0:
                print(f"⏱️  Free fall timeout (no impact), returning to IDLE")
                self._transition_to_state(FallDetectionState.IDLE)
        
        elif self.state == FallDetectionState.IMPACT:
            # Monitor for inactivity (person lying still)
            # Inactivity = acceleration stable around 1G (resting on ground)
            is_inactive = abs(self.current_total_accel - 1.0) < 0.2  # Within 0.8G - 1.2G
            
            if is_inactive and time_in_state >= self.inactivity_duration:
                # Fall detected!
                self._transition_to_state(FallDetectionState.INACTIVITY)
                print(f"🚨 FALL DETECTED! (inactivity: {time_in_state:.1f}s)")
                await self._handle_fall_detected()
            
            elif not is_inactive and time_in_state > 2.0:
                # Person is moving around, probably not a fall
                print(f"✅ Movement detected after impact, likely not a fall")
                self._transition_to_state(FallDetectionState.IDLE)
        
        elif self.state == FallDetectionState.INACTIVITY:
            # Wait for cooldown period
            if time_in_state >= self.cooldown_period:
                print(f"⏱️  Cooldown complete, resuming monitoring")
                self._transition_to_state(FallDetectionState.IDLE)
                self.fall_acknowledged = False  # Reset for next fall
    
    def _transition_to_state(self, new_state: FallDetectionState):
        """Transition to a new state and reset timer"""
        self.state = new_state
        self.state_start_time = time.time()
    
    async def _handle_fall_detected(self):
        """
        Handle fall detection event
        - Store event data for polling endpoint
        - Trigger callback (TTS, video cutoff, etc.)
        """
        # Create fall event data
        self.latest_fall_event = {
            'timestamp': datetime.now().isoformat() + 'Z',
            'freefall_g': round(self.free_fall_magnitude, 2) if self.free_fall_magnitude else None,
            'impact_g': round(self.impact_magnitude, 2) if self.impact_magnitude else None,
            'inactivity_sec': round(time.time() - self.impact_time, 1) if self.impact_time else None,
            'user_response': None,  # Will be updated by STT confirmation
            'acknowledged': False
        }
        
        print(f"📋 Fall event logged: {self.latest_fall_event}")
        
        # Trigger callback (if registered)
        if self.on_fall_detected:
            try:
                await self.on_fall_detected(self.latest_fall_event)
            except Exception as e:
                print(f"❌ Error in fall detection callback: {e}")
    
    def acknowledge_fall(self, user_confirmed: bool, response_text: Optional[str] = None):
        """
        Acknowledge fall event (called after user confirmation or timeout)
        
        Args:
            user_confirmed: True if user said "okay", False if timeout/no response
            response_text: The actual text user said (for logging)
        """
        if self.latest_fall_event:
            self.latest_fall_event['acknowledged'] = True
            self.latest_fall_event['user_response'] = 'CONFIRMED' if user_confirmed else 'NO_RESPONSE'
            self.latest_fall_event['response_text'] = response_text
            self.fall_acknowledged = True
            
            print(f"✅ Fall acknowledged: {self.latest_fall_event['user_response']}")
    
    def get_current_readings(self) -> Dict[str, Any]:
        """Get current accelerometer readings"""
        return {
            'acceleration': {
                'x': round(self.current_accel['x'], 2),
                'y': round(self.current_accel['y'], 2),
                'z': round(self.current_accel['z'], 2),
                'total': round(self.current_total_accel, 2)
            },
            'state': self.state.value,
            'time_in_state': round(time.time() - self.state_start_time, 1)
        }
    
    def get_emergency_status(self) -> Dict[str, Any]:
        """
        Get emergency status for polling endpoint
        Returns the latest fall event and current state
        """
        return {
            'monitoring': self.is_running,
            'current_state': self.state.value,
            'latest_fall': self.latest_fall_event,
            'current_readings': self.get_current_readings() if self.is_running else None
        }
    
    async def simulate_fall(self):
        """
        Simulate a fall for testing purposes
        Manually triggers the fall detection callback
        """
        print("🧪 Simulating fall event...")
        
        # Create simulated fall event
        self.latest_fall_event = {
            'timestamp': datetime.now().isoformat() + 'Z',
            'freefall_g': 0.35,
            'impact_g': 2.8,
            'inactivity_sec': 5.2,
            'user_response': None,
            'acknowledged': False,
            'simulated': True
        }
        
        # Trigger callback
        if self.on_fall_detected:
            await self.on_fall_detected(self.latest_fall_event)
        
        # Enter cooldown state
        self._transition_to_state(FallDetectionState.INACTIVITY)


# Singleton accessor
_accelerometer_service: Optional[AccelerometerService] = None

def get_accelerometer_service() -> AccelerometerService:
    """Get the singleton accelerometer service instance"""
    global _accelerometer_service
    if _accelerometer_service is None:
        _accelerometer_service = AccelerometerService()
    return _accelerometer_service

