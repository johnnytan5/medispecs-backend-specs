#!/usr/bin/env python3
"""
Mac Location Tracker
Uses macOS CoreLocation to get your Mac's location and uploads to API Gateway

Features:
- Uses macOS CoreLocation framework (no GPS hardware needed)
- Comprehensive logging
- Automatic retry on failures
- Configurable sampling interval

Setup:
1. Install dependencies: pip3 install requests pyobjc-framework-CoreLocation
2. Grant location permissions when prompted (System Preferences > Security & Privacy > Location Services)
3. Configure device_id and api_url below
4. Run: python3 mac_location_tracker.py

Logging:
- All logs go to console (stdout/stderr)
- Use log file option for production
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

# ============================================================================
# CONFIGURATION
# ============================================================================

# Device ID (change this to your device ID)
DEVICE_ID = os.environ.get('DEVICE_ID', 'd_123')

# API Gateway URL
API_BASE_URL = os.environ.get(
    'API_BASE_URL',
    'https://zqglpdheqk.execute-api.ap-southeast-1.amazonaws.com/staging'
)

# Location sampling interval (seconds)
SAMPLING_INTERVAL = int(os.environ.get('SAMPLING_INTERVAL', '60'))  # 1 minute default

# Logging Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
LOG_FILE = os.environ.get('LOG_FILE', None)  # Optional: log to file

# Location accuracy threshold (meters) - filter out low accuracy readings
MIN_ACCURACY = float(os.environ.get('MIN_ACCURACY', '100.0'))  # 100m default

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Configure logging with timestamps and levels"""
    log_format = '%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if LOG_FILE:
        handlers.append(logging.FileHandler(LOG_FILE))
    
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================================
# MACOS LOCATION INTERFACE
# ============================================================================

@dataclass
class Location:
    """Location data structure"""
    lat: float
    lng: float
    accuracy: Optional[float] = None
    speed: Optional[float] = None
    timestamp: Optional[str] = None

class MacLocationManager:
    """macOS CoreLocation manager"""
    
    def __init__(self):
        self.location_manager = None
        self.initialized = False
        self.last_location = None
        self._setup_location_manager()
    
    def _setup_location_manager(self):
        """Initialize CoreLocation manager"""
        try:
            from CoreLocation import CLLocationManager, kCLAuthorizationStatusAuthorized, kCLAuthorizationStatusNotDetermined
            from Foundation import NSRunLoop, NSDefaultRunLoopMode
            
            self.location_manager = CLLocationManager.alloc().init()
            self.NSRunLoop = NSRunLoop
            self.NSDefaultRunLoopMode = NSDefaultRunLoopMode
            self.kCLAuthorizationStatusAuthorized = kCLAuthorizationStatusAuthorized
            self.kCLAuthorizationStatusNotDetermined = kCLAuthorizationStatusNotDetermined
            
            # Request authorization
            auth_status = self.location_manager.authorizationStatus()
            
            if auth_status == self.kCLAuthorizationStatusNotDetermined:
                logger.info("📍 Requesting location permission...")
                self.location_manager.requestAlwaysAuthorization()
                # Wait a moment for permission dialog
                time.sleep(1)
            
            auth_status = self.location_manager.authorizationStatus()
            
            if auth_status == self.kCLAuthorizationStatusAuthorized:
                logger.info("✅ Location permission granted")
                self.initialized = True
            else:
                logger.warning("⚠️  Location permission not granted")
                logger.info("💡 Please enable location services in:")
                logger.info("   System Preferences > Security & Privacy > Location Services")
                self.initialized = False
            
        except ImportError:
            logger.error("❌ CoreLocation framework not available")
            logger.info("💡 Install with: pip3 install pyobjc-framework-CoreLocation")
            self.initialized = False
        except Exception as e:
            logger.error(f"❌ Failed to initialize location manager: {e}")
            self.initialized = False
    
    def get_location(self) -> Optional[Location]:
        """Get current location from macOS"""
        if not self.initialized:
            return None
        
        try:
            from CoreLocation import CLLocation
            
            # Start location updates
            self.location_manager.startUpdatingLocation()
            
            # Wait a moment for location to be acquired
            time.sleep(2)
            
            # Get the most recent location
            location = self.location_manager.location()
            
            if location is None:
                logger.debug("⚠️  No location available yet (waiting for GPS/WiFi positioning...)")
                self.location_manager.stopUpdatingLocation()
                return None
            
            # Extract coordinates
            coord = location.coordinate()
            lat = coord.latitude
            lng = coord.longitude
            
            # Extract accuracy (horizontal accuracy in meters)
            accuracy = location.horizontalAccuracy()
            
            # Extract speed (meters per second)
            speed = location.speed()
            if speed < 0:  # Negative speed means invalid
                speed = None
            
            # Stop location updates
            self.location_manager.stopUpdatingLocation()
            
            # Filter by accuracy
            if accuracy > MIN_ACCURACY:
                logger.debug(f"⚠️  Location accuracy too low: {accuracy:.1f}m (threshold: {MIN_ACCURACY}m)")
                return None
            
            return Location(
                lat=lat,
                lng=lng,
                accuracy=accuracy if accuracy > 0 else None,
                speed=speed if speed and speed > 0 else None,
                timestamp=datetime.utcnow().isoformat() + 'Z'
            )
        
        except Exception as e:
            logger.debug(f"⚠️  Location read error: {e}")
            if self.location_manager:
                try:
                    self.location_manager.stopUpdatingLocation()
                except:
                    pass
            return None
    
    def is_available(self) -> bool:
        """Check if location services are available"""
        if not self.initialized:
            return False
        
        try:
            from CoreLocation import kCLAuthorizationStatusAuthorized
            auth_status = self.location_manager.authorizationStatus()
            return auth_status == kCLAuthorizationStatusAuthorized
        except:
            return False

# ============================================================================
# API UPLOAD
# ============================================================================

def upload_location(location: Location) -> bool:
    """Upload single location to API Gateway"""
    payload = {
        'deviceId': DEVICE_ID,
        'locations': [{
            'lat': location.lat,
            'lng': location.lng,
            'timestamp': location.timestamp or datetime.utcnow().isoformat() + 'Z',
        }]
    }
    
    if location.accuracy is not None:
        payload['locations'][0]['accuracy'] = location.accuracy
    if location.speed is not None:
        payload['locations'][0]['speed'] = location.speed
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/locations",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code in [201, 207]:
            result = response.json()
            count = result.get('count', 1)
            logger.info(f"✅ Location uploaded successfully (count={count})")
            return True
        else:
            logger.error(f"❌ API upload failed: HTTP {response.status_code} - {response.text}")
            return False
    
    except requests.exceptions.Timeout:
        logger.error("❌ API upload timeout (server not responding)")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("❌ API upload connection error (check network/API URL)")
        return False
    except Exception as e:
        logger.error(f"❌ API upload error: {e}")
        return False

# ============================================================================
# MAIN LOOP
# ============================================================================

def main():
    """Main tracking loop"""
    logger.info("=" * 60)
    logger.info("🍎 Mac Location Tracker Starting")
    logger.info("=" * 60)
    logger.info(f"Device ID: {DEVICE_ID}")
    logger.info(f"API URL: {API_BASE_URL}")
    logger.info(f"Sampling Interval: {SAMPLING_INTERVAL} seconds")
    logger.info(f"Min Accuracy: {MIN_ACCURACY} meters")
    logger.info(f"Log Level: {LOG_LEVEL}")
    logger.info("=" * 60)
    
    # Initialize location manager
    logger.info("📍 Initializing macOS Location Services...")
    location_manager = MacLocationManager()
    
    if not location_manager.initialized:
        logger.error("❌ Location services initialization failed. Exiting.")
        logger.info("")
        logger.info("💡 Troubleshooting:")
        logger.info("   1. Install CoreLocation: pip3 install pyobjc-framework-CoreLocation")
        logger.info("   2. Enable Location Services: System Preferences > Security & Privacy > Location Services")
        logger.info("   3. Grant permission to Terminal/Python when prompted")
        return 1
    
    logger.info("✅ Location services initialized successfully")
    logger.info("=" * 60)
    logger.info("📍 Starting location tracking loop...")
    logger.info("=" * 60)
    
    consecutive_failures = 0
    max_failures = 5
    no_location_count = 0
    
    try:
        while True:
            # Get location
            location = location_manager.get_location()
            
            if location:
                logger.info(f"📍 Location: lat={location.lat:.6f}, lng={location.lng:.6f}, "
                          f"accuracy={location.accuracy:.1f}m" if location.accuracy else "accuracy=N/A")
                
                if location.speed:
                    logger.info(f"   Speed: {location.speed:.2f} m/s ({location.speed * 3.6:.1f} km/h)")
                
                # Upload to API
                if upload_location(location):
                    consecutive_failures = 0
                    no_location_count = 0
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logger.warning(f"⚠️  {consecutive_failures} consecutive upload failures. "
                                     f"Location tracking still working, but API uploads are failing.")
            else:
                no_location_count += 1
                if no_location_count == 1:
                    logger.debug("⚠️  No location available (waiting for location services...)")
                elif no_location_count % 10 == 0:
                    logger.warning(f"⚠️  Still waiting for location ({no_location_count} attempts)")
                    logger.info("💡 Make sure Location Services is enabled and you have WiFi/Internet connection")
                
                if not location_manager.is_available():
                    logger.warning("⚠️  Location services not available. Check permissions.")
            
            # Wait for next sample
            time.sleep(SAMPLING_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 60)
        logger.info("🛑 Location tracker stopped by user")
        logger.info("=" * 60)
        return 0
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())

