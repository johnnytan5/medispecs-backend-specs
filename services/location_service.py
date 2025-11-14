"""
Location Service - Neo-6M GPS Location Tracking
Reads GPS location every second and uploads to Lambda API Gateway in batches
"""
import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
import requests

# Try to import serial (pyserial)
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("⚠️  pyserial not installed. Location tracking will be disabled.")

# Try to import pynmea2
try:
    import pynmea2
    NMEA_AVAILABLE = True
except ImportError:
    NMEA_AVAILABLE = False
    print("⚠️  pynmea2 not installed. Location tracking will be disabled.")


class LocationService:
    """
    Service for tracking GPS location using Neo-6M GPS module
    
    Features:
    - Reads GPS location every 1 second via serial/UART
    - Buffers locations in memory
    - Sends batches to Lambda API Gateway every 10 seconds
    - Handles GPS fix status and errors gracefully
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
        self.gps_task: Optional[asyncio.Task] = None
        self.upload_task: Optional[asyncio.Task] = None
        
        # GPS serial connection
        self.serial_conn: Optional[serial.Serial] = None
        
        # Configuration (will be set by initialize())
        self.device_id = "d_123"
        self.lambda_url = ""
        self.update_interval = 1  # Read GPS every 1 second
        self.batch_interval = 10  # Send batch every 10 seconds
        self.gps_port = "/dev/ttyAMA0"
        self.gps_baudrate = 9600
        
        # Location buffer
        self.location_buffer: List[Dict[str, Any]] = []
        self.buffer_lock = asyncio.Lock()
        
        # Current GPS status
        self.current_location: Optional[Dict[str, Any]] = None
        self.has_fix = False
        self.last_fix_time: Optional[datetime] = None
        
        # Statistics
        self.locations_read = 0
        self.locations_sent = 0
        self.upload_errors = 0
        self.last_upload_time: Optional[datetime] = None
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize location service with configuration
        
        Args:
            config: Dictionary with location settings from config.py
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            if not SERIAL_AVAILABLE or not NMEA_AVAILABLE:
                print("❌ Location service dependencies not available")
                return False
            
            # Load configuration
            self.device_id = config.get('LOCATION_DEVICE_ID', 'd_123')
            self.lambda_url = config.get('LOCATION_LAMBDA_URL', '')
            self.update_interval = config.get('LOCATION_UPDATE_INTERVAL', 1)
            self.batch_interval = config.get('LOCATION_BATCH_INTERVAL', 10)
            self.gps_port = config.get('LOCATION_GPS_PORT', '/dev/ttyAMA0')
            self.gps_baudrate = config.get('LOCATION_GPS_BAUDRATE', 9600)
            
            if not self.lambda_url:
                print("⚠️  Location Lambda URL not configured")
                return False
            
            print(f"✅ Location service initialized")
            print(f"   Device ID: {self.device_id}")
            print(f"   GPS Port: {self.gps_port}")
            print(f"   Update interval: {self.update_interval}s")
            print(f"   Batch interval: {self.batch_interval}s")
            
            return True
            
        except Exception as e:
            print(f"❌ Location service initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def start(self):
        """Start location tracking service"""
        if not SERIAL_AVAILABLE or not NMEA_AVAILABLE:
            print("⏸️  Location tracking disabled (dependencies not available)")
            return
        
        if self.is_running:
            print("⚠️  Location tracking is already running")
            return
        
        # Open GPS serial connection
        try:
            print(f"📡 Opening GPS serial port: {self.gps_port}")
            self.serial_conn = serial.Serial(
                port=self.gps_port,
                baudrate=self.gps_baudrate,
                timeout=1.0
            )
            print(f"✅ GPS serial port opened successfully")
        except Exception as e:
            print(f"❌ Failed to open GPS serial port: {e}")
            print(f"   Make sure GPS module is connected and UART is enabled")
            return
        
        self.is_running = True
        
        # Start GPS reading task
        self.gps_task = asyncio.create_task(self._gps_reading_loop())
        
        # Start batch upload task
        self.upload_task = asyncio.create_task(self._batch_upload_loop())
        
        print(f"📍 Location tracking started")
        print(f"   Reading GPS every {self.update_interval}s")
        print(f"   Uploading batches every {self.batch_interval}s")
    
    async def stop(self):
        """Stop location tracking service"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel tasks
        if self.gps_task:
            self.gps_task.cancel()
            try:
                await self.gps_task
            except asyncio.CancelledError:
                pass
        
        if self.upload_task:
            self.upload_task.cancel()
            try:
                await self.upload_task
            except asyncio.CancelledError:
                pass
        
        # Close serial connection
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("📡 GPS serial port closed")
        
        # Upload any remaining buffered locations
        await self._upload_batch()
        
        print("🛑 Location tracking stopped")
    
    async def _gps_reading_loop(self):
        """Continuously read GPS location from serial port"""
        print("📡 GPS reading loop started")
        
        while self.is_running:
            try:
                # Read GPS data
                location = await self._read_gps_location()
                
                if location:
                    # Update current location
                    self.current_location = location
                    self.has_fix = True
                    self.last_fix_time = datetime.now()
                    self.locations_read += 1
                    
                    # Add to buffer
                    async with self.buffer_lock:
                        self.location_buffer.append(location)
                    
                    # Log every 10 readings (to avoid spam)
                    if self.locations_read % 10 == 0:
                        print(f"📍 GPS Fix: lat={location['lat']:.6f}, lng={location['lng']:.6f}, accuracy={location.get('accuracy', 'N/A')}")
                else:
                    self.has_fix = False
                
                # Wait for next update interval
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Error reading GPS: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _read_gps_location(self) -> Optional[Dict[str, Any]]:
        """
        Read GPS location from serial port
        
        Returns:
            Dict with lat, lng, timestamp, accuracy, speed or None if no fix
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            return None
        
        try:
            # Read line from GPS (NMEA sentence)
            line = await asyncio.to_thread(self.serial_conn.readline)
            
            if not line:
                return None
            
            # Decode bytes to string
            try:
                line_str = line.decode('utf-8').strip()
            except UnicodeDecodeError:
                return None
            
            # Parse NMEA sentence
            try:
                msg = pynmea2.parse(line_str)
                
                # We're looking for GGA (Global Positioning System Fix Data) or RMC (Recommended Minimum)
                if isinstance(msg, pynmea2.types.talker.GGA):
                    # GGA sentence contains lat, lon, altitude, fix quality
                    if msg.latitude == 0.0 and msg.longitude == 0.0:
                        return None  # No valid fix
                    
                    if msg.gps_qual == 0:
                        return None  # No GPS fix
                    
                    location = {
                        'lat': float(msg.latitude),
                        'lng': float(msg.longitude),
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'accuracy': float(msg.horizontal_dil) if msg.horizontal_dil else None,
                    }
                    
                    return location
                
                elif isinstance(msg, pynmea2.types.talker.RMC):
                    # RMC sentence contains lat, lon, speed, course, date/time
                    if msg.latitude == 0.0 and msg.longitude == 0.0:
                        return None  # No valid fix
                    
                    if msg.status != 'A':  # 'A' = Active (valid fix)
                        return None  # No valid fix
                    
                    location = {
                        'lat': float(msg.latitude),
                        'lng': float(msg.longitude),
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'speed': float(msg.spd_over_grnd) if msg.spd_over_grnd else None,
                    }
                    
                    return location
                
            except pynmea2.ParseError:
                # Not a valid NMEA sentence, skip
                return None
            except Exception as e:
                # Other parsing error
                return None
        
        except Exception as e:
            return None
        
        return None
    
    async def _batch_upload_loop(self):
        """Continuously upload location batches to Lambda"""
        print("📤 Batch upload loop started")
        
        while self.is_running:
            try:
                # Wait for batch interval
                await asyncio.sleep(self.batch_interval)
                
                # Upload batch
                await self._upload_batch()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Error in batch upload loop: {e}")
                await asyncio.sleep(self.batch_interval)
    
    async def _upload_batch(self):
        """Upload buffered locations to Lambda API Gateway"""
        async with self.buffer_lock:
            if len(self.location_buffer) == 0:
                return
            
            # Get batch (copy and clear buffer)
            batch = self.location_buffer.copy()
            self.location_buffer.clear()
        
        if len(batch) == 0:
            return
        
        try:
            # Prepare request payload
            payload = {
                'deviceId': self.device_id,
                'locations': batch
            }
            
            # Send to Lambda
            url = f"{self.lambda_url}/locations"
            
            response = await asyncio.to_thread(
                requests.post,
                url,
                json=payload,
                timeout=10.0
            )
            
            response.raise_for_status()
            
            result = response.json()
            count = result.get('count', len(batch))
            
            self.locations_sent += count
            self.last_upload_time = datetime.now()
            
            print(f"✅ Uploaded {count} location(s) to Lambda")
            
        except requests.exceptions.RequestException as e:
            self.upload_errors += 1
            print(f"❌ Failed to upload locations: {e}")
            
            # Put locations back in buffer (at the front) for retry
            async with self.buffer_lock:
                self.location_buffer = batch + self.location_buffer
            
        except Exception as e:
            self.upload_errors += 1
            print(f"❌ Error uploading locations: {e}")
            import traceback
            traceback.print_exc()
            
            # Put locations back in buffer for retry
            async with self.buffer_lock:
                self.location_buffer = batch + self.location_buffer
    
    def get_status(self) -> Dict[str, Any]:
        """Get current location service status"""
        return {
            'is_running': self.is_running,
            'has_fix': self.has_fix,
            'current_location': self.current_location,
            'last_fix_time': self.last_fix_time.isoformat() if self.last_fix_time else None,
            'buffer_size': len(self.location_buffer),
            'locations_read': self.locations_read,
            'locations_sent': self.locations_sent,
            'upload_errors': self.upload_errors,
            'last_upload_time': self.last_upload_time.isoformat() if self.last_upload_time else None,
        }


# Singleton accessor
_location_service: Optional[LocationService] = None

def get_location_service() -> LocationService:
    """Get the singleton location service instance"""
    global _location_service
    if _location_service is None:
        _location_service = LocationService()
    return _location_service

