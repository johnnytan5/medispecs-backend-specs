"""
Medication Service - Medication Reminder & Verification System
Manages medication schedules, polling from Lambda, and triggering detection
"""
import asyncio
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests
import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger


class MedicationService:
    """
    Service for managing medication schedules and detection
    
    Features:
    - SQLite storage for medications
    - Poll Lambda API every 2 hours for medication updates
    - Check for due medications every minute
    - Trigger 5-minute detection window when medication is due
    - Coordinate with medication detection service
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
        self.db_path: Optional[Path] = None
        self.is_running = False
        self.scheduler: Optional[AsyncIOScheduler] = None
        
        # Configuration (will be set by initialize())
        self.lambda_url = ""
        self.poll_interval = 7200  # 2 hours
        self.check_interval = 60  # 1 minute
        self.detection_window_minutes = 5
        
        # Detection service callback
        self.detection_service = None  # Will be set by main.py
        
        # Active detection tracking
        self.active_detection: Optional[Dict[str, Any]] = None  # Current medication being detected
        self.triggered_today: Dict[str, str] = {}  # Track medications triggered today (medication_id -> date)
        self.last_check_date: Optional[str] = None  # Track last date checked (for resetting triggered_today)
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize medication service with configuration
        
        Args:
            config: Dictionary with medication settings from config.py
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Load configuration
            self.db_path = Path(config.get('MEDICATION_DB_PATH', 'medications.db'))
            self.lambda_url = config.get('MEDICATION_LAMBDA_URL', '')
            self.poll_interval = config.get('MEDICATION_POLL_INTERVAL', 7200)
            self.check_interval = config.get('MEDICATION_CHECK_INTERVAL', 60)
            self.detection_window_minutes = config.get('MEDICATION_DETECTION_WINDOW', 5)
            
            # Initialize database
            self._init_database()
            
            # Initialize scheduler
            self.scheduler = AsyncIOScheduler()
            
            print(f"✅ Medication service initialized")
            print(f"   Database: {self.db_path}")
            print(f"   Poll interval: {self.poll_interval//3600}h")
            print(f"   Detection window: {self.detection_window_minutes} minutes")
            
            return True
            
        except Exception as e:
            print(f"❌ Medication service initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _init_database(self):
        """Initialize SQLite database with schema"""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        cursor = conn.cursor()
        
        # Medications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medications (
                medication_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                time TEXT NOT NULL,
                frequency TEXT DEFAULT 'daily',
                frequency_details TEXT,
                photo_url TEXT,
                photo_s3_key TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_synced_at TEXT,
                version INTEGER DEFAULT 1
            )
        ''')
        
        # Detection history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medication_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medication_id TEXT NOT NULL,
                detection_time TEXT NOT NULL,
                detected BOOLEAN NOT NULL,
                match_result BOOLEAN,
                confidence REAL,
                photo_path TEXT,
                notes TEXT,
                FOREIGN KEY (medication_id) REFERENCES medications(medication_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def start(self):
        """Start medication service"""
        if self.is_running:
            print("⚠️  Medication service already running")
            return
        
        self.is_running = True
        
        # Start scheduler
        self.scheduler.start()
        
        # Schedule polling job (every 2 hours)
        self.scheduler.add_job(
            self._poll_medications,
            trigger=IntervalTrigger(seconds=self.poll_interval),
            id='medication_poll',
            replace_existing=True
        )
        
        # Schedule check job (every minute)
        self.scheduler.add_job(
            self._check_due_medications,
            trigger=IntervalTrigger(seconds=self.check_interval),
            id='medication_check',
            replace_existing=True
        )
        
        # Initial sync
        await self._poll_medications()
        
        print(f"💊 Medication service started")
        print(f"   Polling Lambda every {self.poll_interval//3600} hours")
        print(f"   Checking for due medications every {self.check_interval} seconds")
    
    async def stop(self):
        """Stop medication service"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.scheduler:
            self.scheduler.shutdown(wait=True)
        
        print("🛑 Medication service stopped")
    
    async def _poll_medications(self):
        """Poll Lambda API for medication updates"""
        if not self.lambda_url:
            print("⚠️  LAMBDA_API_URL not configured, skipping medication sync")
            return
        
        try:
            print(f"\n🔄 Polling medications from Lambda...")
            
            # Fetch medications from Lambda
            response = await asyncio.to_thread(
                requests.get,
                f"{self.lambda_url}/medications",
                params={'userId': 'u_123'},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to fetch medications: {response.status_code}")
                return
            
            medications = response.json()
            print(f"📋 Received {len(medications)} medications from Lambda")
            
            # Sync to local database
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            cursor = conn.cursor()
            
            synced_count = 0
            for med in medications:
                medication_id = med.get('medicationId')
                if not medication_id:
                    continue
                
                # Insert or update
                cursor.execute('''
                    INSERT OR REPLACE INTO medications (
                        medication_id, name, time, frequency, frequency_details,
                        photo_url, photo_s3_key, notes,
                        created_at, updated_at, last_synced_at, version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    medication_id,
                    med.get('name', ''),
                    med.get('time', ''),
                    med.get('frequency', 'daily'),
                    json.dumps(med.get('frequencyDetails', [])) if med.get('frequencyDetails') else None,
                    med.get('photoUrl', ''),
                    med.get('photoS3Key', ''),
                    med.get('notes', ''),
                    med.get('createdAt', datetime.now().isoformat() + 'Z'),
                    med.get('updatedAt', datetime.now().isoformat() + 'Z'),
                    datetime.now().isoformat() + 'Z',
                    med.get('version', 1)
                ))
                synced_count += 1
            
            conn.commit()
            conn.close()
            
            print(f"✅ Synced {synced_count} medications to local database")
            
        except Exception as e:
            print(f"❌ Error polling medications: {e}")
            import traceback
            traceback.print_exc()
    
    async def _check_due_medications(self):
        """Check for medications that are due now (within 5-minute window)"""
        if not self.is_running:
            return
        
        try:
            # Get current time
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")
            current_date = now.strftime("%Y-%m-%d")
            
            # Reset triggered_today if date changed
            if self.last_check_date and self.last_check_date != current_date:
                print(f"📅 New day detected, resetting medication triggers")
                self.triggered_today = {}
            self.last_check_date = current_date
            
            # Parse current time to minutes since midnight
            current_hour, current_minute = map(int, current_time_str.split(':'))
            current_minutes = current_hour * 60 + current_minute
            
            # Get all medications
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM medications')
            medications = cursor.fetchall()
            
            conn.close()
            
            # Check each medication
            for med_row in medications:
                medication_id = med_row[0]
                name = med_row[1]
                scheduled_time_str = med_row[2]
                
                # Check if already triggered today
                if self.triggered_today.get(medication_id) == current_date:
                    continue  # Already triggered today
                
                # Check if we're already detecting this medication
                if self.active_detection and self.active_detection.get('medication_id') == medication_id:
                    continue  # Already detecting
                
                # Parse scheduled time
                try:
                    scheduled_hour, scheduled_minute = map(int, scheduled_time_str.split(':'))
                    scheduled_minutes = scheduled_hour * 60 + scheduled_minute
                except:
                    continue  # Invalid time format
                
                # Check if we're within the detection window (0-5 minutes after scheduled time)
                time_diff = current_minutes - scheduled_minutes
                
                if 0 <= time_diff <= self.detection_window_minutes:
                    # Within window! Trigger detection
                    print(f"⏰ Medication '{name}' is due (scheduled: {scheduled_time_str}, current: {current_time_str})")
                    await self._trigger_medication_detection(medication_id, name, scheduled_time_str)
                    # Mark as triggered today
                    self.triggered_today[medication_id] = current_date
            
        except Exception as e:
            print(f"❌ Error checking due medications: {e}")
            import traceback
            traceback.print_exc()
    
    async def _trigger_medication_detection(self, medication_id: str, name: str, scheduled_time: str):
        """
        Trigger medication detection for a due medication
        
        Args:
            medication_id: Medication ID
            name: Medication name
            scheduled_time: Scheduled time (HH:MM)
        """
        print(f"\n{'='*60}")
        print(f"💊 Medication Due: {name} ({scheduled_time})")
        print(f"{'='*60}")
        
        # Get medication details
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM medications WHERE medication_id = ?', (medication_id,))
        med_row = cursor.fetchone()
        conn.close()
        
        if not med_row:
            print(f"❌ Medication not found: {medication_id}")
            return
        
        photo_url = med_row[5]  # photo_url column
        
        # Build full photo URL if it's a relative path
        if photo_url and not photo_url.startswith('http'):
            # Lambda returns relative URL like "/medications/{id}/photo"
            # Prepend Lambda base URL
            if photo_url.startswith('/'):
                photo_url = f"{self.lambda_url}{photo_url}"
            else:
                photo_url = f"{self.lambda_url}/medications/{medication_id}/photo"
        
        if not photo_url:
            print(f"⚠️  No photo URL for medication {medication_id}, detection will skip verification")
        
        # Set active detection
        self.active_detection = {
            'medication_id': medication_id,
            'name': name,
            'scheduled_time': scheduled_time,
            'photo_url': photo_url,
            'start_time': datetime.now(),
            'window_end': datetime.now() + timedelta(minutes=self.detection_window_minutes)
        }
        
        # Play reminder TTS and show OLED
        from services.tts_service import get_tts_service
        from services.oled_display import get_oled_service
        import config
        
        tts = get_tts_service()
        oled = get_oled_service()
        
        # Fire and forget for TTS and OLED
        tts_task = asyncio.create_task(tts.speak_async(config.MEDICATION_TTS_REMINDER))
        oled_task = asyncio.create_task(asyncio.to_thread(oled.show_message, config.MEDICATION_OLED_REMINDER))
        
        await asyncio.gather(tts_task, oled_task)
        
        # Start detection (if detection service is available)
        if self.detection_service:
            print(f"🔍 Starting medication detection (5 minute window)...")
            print(f"   Detection service type: {type(self.detection_service).__name__}")
            print(f"   Detection service initialized: {self.detection_service.model is not None if hasattr(self.detection_service, 'model') else 'N/A'}")
            try:
                await self.detection_service.start_detection(
                    medication_id=medication_id,
                    medication_name=name,
                    reference_photo_url=photo_url,
                    window_duration_seconds=self.detection_window_minutes * 60
                )
                print(f"✅ Detection service started successfully")
            except Exception as e:
                print(f"❌ Error starting detection service: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️  Detection service not available (self.detection_service is None)")
            print(f"   This means detection service was not wired in main.py")
        
        # Schedule cleanup after window expires
        asyncio.create_task(self._clear_active_detection_after_window())
    
    async def _clear_active_detection_after_window(self):
        """Clear active detection after window expires"""
        if not self.active_detection:
            return
        
        window_end = self.active_detection['window_end']
        wait_seconds = (window_end - datetime.now()).total_seconds()
        
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)
        
        # Clear active detection
        if self.active_detection:
            print(f"⏱️  Detection window expired for {self.active_detection['name']}")
            self.active_detection = None
    
    def record_detection_result(self, medication_id: str, detected: bool, match_result: Optional[bool], 
                                confidence: Optional[float], photo_path: Optional[str] = None):
        """
        Record medication detection result to database
        
        Args:
            medication_id: Medication ID
            detected: Whether medication bottle was detected
            match_result: Whether detected bottle matches reference (True/False/None)
            confidence: Confidence score from OpenAI Vision
            photo_path: Path to captured photo (optional)
        """
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO medication_detections (
                    medication_id, detection_time, detected, match_result, confidence, photo_path
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                medication_id,
                datetime.now().isoformat() + 'Z',
                detected,
                match_result,
                confidence,
                photo_path
            ))
            
            conn.commit()
            conn.close()
            
            print(f"📝 Recorded detection result: detected={detected}, match={match_result}, confidence={confidence}")
            
        except Exception as e:
            print(f"❌ Error recording detection result: {e}")
    
    def get_medications(self) -> List[Dict[str, Any]]:
        """Get all medications from database"""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM medications ORDER BY time')
            rows = cursor.fetchall()
            
            conn.close()
            
            medications = []
            for row in rows:
                medications.append({
                    'medication_id': row[0],
                    'name': row[1],
                    'time': row[2],
                    'frequency': row[3],
                    'frequency_details': json.loads(row[4]) if row[4] else [],
                    'photo_url': row[5],
                    'photo_s3_key': row[6],
                    'notes': row[7],
                    'created_at': row[8],
                    'updated_at': row[9],
                    'last_synced_at': row[10],
                    'version': row[11]
                })
            
            return medications
            
        except Exception as e:
            print(f"❌ Error getting medications: {e}")
            return []
    
    def get_detection_history(self, medication_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get detection history"""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            cursor = conn.cursor()
            
            if medication_id:
                cursor.execute('''
                    SELECT * FROM medication_detections 
                    WHERE medication_id = ? 
                    ORDER BY detection_time DESC 
                    LIMIT ?
                ''', (medication_id, limit))
            else:
                cursor.execute('''
                    SELECT * FROM medication_detections 
                    ORDER BY detection_time DESC 
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            detections = []
            for row in rows:
                detections.append({
                    'id': row[0],
                    'medication_id': row[1],
                    'detection_time': row[2],
                    'detected': bool(row[3]),
                    'match_result': bool(row[4]) if row[4] is not None else None,
                    'confidence': row[5],
                    'photo_path': row[6],
                    'notes': row[7]
                })
            
            return detections
            
        except Exception as e:
            print(f"❌ Error getting detection history: {e}")
            return []


# Singleton accessor
_medication_service: Optional[MedicationService] = None

def get_medication_service() -> MedicationService:
    """Get the singleton medication service instance"""
    global _medication_service
    if _medication_service is None:
        _medication_service = MedicationService()
    return _medication_service

