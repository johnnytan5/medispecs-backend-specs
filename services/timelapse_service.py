"""
Timelapse Recording Service for MediSpecs
Captures frames from camera and creates timelapse videos

Features:
- Automatic frame capture (1 frame / 2 seconds)
- 15-minute video segments (450 frames)
- Upload to S3 via Lambda API Gateway  
- SQLite tracking for retry logic
- Auto-cleanup after 24 hours
"""

import asyncio
import os
import time
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import requests
import cv2
import numpy as np


class TimelapseService:
    """
    Timelapse recording service
    
    Flow:
    1. Capture frames every 2 seconds from camera
    2. After 450 frames (15 min), create MP4 video
    3. Upload to S3 via Lambda API Gateway
    4. Track in SQLite for retry logic
    5. Cleanup videos older than 24 hours
    """
    
    def __init__(self):
        self.is_running = False
        self.is_recording = False
        
        # Configuration (loaded on initialize)
        self.frame_interval = 2
        self.segment_duration = 900  # 15 minutes
        self.video_fps = 30
        self.video_quality = 80
        self.storage_path = "timelapse"
        self.max_age_hours = 24
        
        # Current segment tracking
        self.current_segment_id: Optional[str] = None
        self.current_segment_frames: List[np.ndarray] = []
        self.current_segment_start_time: Optional[datetime] = None
        self.frames_captured = 0
        
        # Tasks
        self.capture_task: Optional[asyncio.Task] = None
        self.retry_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Database
        self.db_path: Optional[str] = None
        
    def initialize(self, config: dict):
        """
        Initialize timelapse service
        
        Args:
            config: Configuration dictionary from config.py
        """
        print("🎬 Initializing Timelapse service...")
        
        try:
            # Load configuration
            self.frame_interval = config.get('TIMELAPSE_FRAME_INTERVAL', 2)
            self.segment_duration = config.get('TIMELAPSE_SEGMENT_DURATION', 900)
            self.video_fps = config.get('TIMELAPSE_VIDEO_FPS', 30)
            self.video_quality = config.get('TIMELAPSE_VIDEO_QUALITY', 80)
            self.storage_path = config.get('TIMELAPSE_STORAGE_PATH', 'timelapse')
            self.max_age_hours = config.get('TIMELAPSE_MAX_AGE_HOURS', 24)
            
            # Create storage directories
            self.pending_dir = Path(self.storage_path) / "pending"
            self.videos_dir = Path(self.storage_path) / "videos"
            self.pending_dir.mkdir(parents=True, exist_ok=True)
            self.videos_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize SQLite database
            self.db_path = Path(self.storage_path) / "timelapse.db"
            self._init_database()
            
            # Calculate expected frames per segment
            self.frames_per_segment = int(self.segment_duration / self.frame_interval)
            
            print(f"   Frame interval: {self.frame_interval}s")
            print(f"   Segment duration: {self.segment_duration}s ({self.segment_duration//60} minutes)")
            print(f"   Frames per segment: {self.frames_per_segment}")
            print(f"   Video FPS: {self.video_fps}")
            print(f"   Storage path: {self.storage_path}")
            print("✅ Timelapse service initialized")
            
            return True
            
        except Exception as e:
            print(f"❌ Timelapse initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _init_database(self):
        """Initialize SQLite database with schema"""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE NOT NULL,
                local_path TEXT NOT NULL,
                s3_key TEXT,
                file_size_bytes INTEGER,
                duration_sec INTEGER,
                frame_count INTEGER,
                recorded_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                uploaded_at TEXT,
                uploaded BOOLEAN DEFAULT 0,
                upload_attempts INTEGER DEFAULT 0,
                last_upload_attempt_at TEXT,
                upload_error TEXT,
                deleted_locally BOOLEAN DEFAULT 0
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_uploaded ON videos(uploaded)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON videos(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_id ON videos(video_id)')
        
        conn.commit()
        conn.close()
    
    async def start(self):
        """Start timelapse recording"""
        if self.is_running:
            print("⚠️  Timelapse service already running")
            return
        
        self.is_running = True
        self.is_recording = True
        
        # Start background tasks
        self.capture_task = asyncio.create_task(self._capture_loop())
        self.retry_task = asyncio.create_task(self._retry_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        print("▶️  Timelapse recording started")
    
    async def stop(self):
        """Stop timelapse recording"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.is_recording = False
        
        # Cancel tasks
        if self.capture_task:
            self.capture_task.cancel()
        if self.retry_task:
            self.retry_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        print("⏹️  Timelapse recording stopped")
    
    async def _capture_loop(self):
        """Main capture loop - captures frames every X seconds"""
        print(f"🔄 Timelapse capture loop started (1 frame every {self.frame_interval}s)")
        
        try:
            while self.is_running and self.is_recording:
                try:
                    # Capture frame
                    await self._capture_frame()
                    
                    # Wait for next interval
                    await asyncio.sleep(self.frame_interval)
                    
                except Exception as e:
                    print(f"❌ Error capturing frame: {e}")
                    await asyncio.sleep(self.frame_interval)
        
        except asyncio.CancelledError:
            print("🔄 Timelapse capture loop cancelled")
        except Exception as e:
            print(f"❌ Fatal error in capture loop: {e}")
            import traceback
            traceback.print_exc()
    
    async def _capture_frame(self):
        """Capture a single frame from camera"""
        try:
            from services.face_detection_service import get_face_detection_service
            
            face_detector = get_face_detection_service()
            
            # Get frame from shared buffer
            async with face_detector.frame_lock:
                if face_detector.latest_frame is not None:
                    frame = face_detector.latest_frame.copy()
                else:
                    # No frame available
                    return
            
            # Initialize new segment if needed
            if self.current_segment_id is None:
                self._start_new_segment()
            
            # Add frame to current segment
            self.current_segment_frames.append(frame)
            self.frames_captured += 1
            
            # Log progress
            if self.frames_captured % 30 == 0:  # Every 30 frames (1 minute)
                elapsed = (datetime.now() - self.current_segment_start_time).total_seconds()
                remaining = self.segment_duration - elapsed
                print(f"   📹 Segment {self.current_segment_id}: {self.frames_captured}/{self.frames_per_segment} frames "
                      f"({remaining/60:.1f} min remaining)")
            
            # Check if segment is complete
            if self.frames_captured >= self.frames_per_segment:
                await self._complete_segment()
                
        except Exception as e:
            print(f"❌ Error in _capture_frame: {e}")
    
    def _start_new_segment(self, prefix: str = ""):
        """
        Start a new video segment
        
        Args:
            prefix: Optional prefix for video ID (e.g., "FALL_" for fall-triggered videos)
        """
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        self.current_segment_id = f"{prefix}{timestamp}"
        self.current_segment_frames = []
        self.current_segment_start_time = datetime.now()
        self.frames_captured = 0
        
        segment_type = "FALL ALERT" if prefix else "regular"
        print(f"\n📹 Starting new segment ({segment_type}): {self.current_segment_id}")
    
    async def _complete_segment(self):
        """Complete current segment and create video"""
        print(f"\n✅ Segment complete: {self.current_segment_id} ({self.frames_captured} frames)")
        print(f"   Creating video...")
        
        try:
            # Create video from frames
            video_path = await self._create_video(
                self.current_segment_id,
                self.current_segment_frames,
                self.current_segment_start_time
            )
            
            if video_path:
                print(f"✅ Video created: {video_path}")
                
                # Upload to S3
                from config import TIMELAPSE_UPLOAD_ENABLED, TIMELAPSE_UPLOAD_IMMEDIATE
                if TIMELAPSE_UPLOAD_ENABLED and TIMELAPSE_UPLOAD_IMMEDIATE:
                    await self._upload_video(self.current_segment_id)
            
            # Reset for next segment
            self.current_segment_id = None
            self.current_segment_frames = []
            self.frames_captured = 0
            
        except Exception as e:
            print(f"❌ Error completing segment: {e}")
            import traceback
            traceback.print_exc()
            
            # Reset anyway to continue recording
            self.current_segment_id = None
            self.current_segment_frames = []
            self.frames_captured = 0
    
    async def trigger_fall_cutoff(self):
        """
        Trigger immediate cutoff for fall detection
        Creates a video with FALL_ prefix and starts a new segment
        
        Returns:
            str: The video ID of the fall segment (with FALL_ prefix)
        """
        if not self.is_recording:
            print("⚠️  Cannot trigger fall cutoff: not recording")
            return None
        
        if not self.current_segment_id:
            print("⚠️  Cannot trigger fall cutoff: no active segment")
            return None
        
        if self.frames_captured == 0:
            print("⚠️  Cannot trigger fall cutoff: no frames captured yet")
            return None
        
        fall_segment_id = self.current_segment_id
        print(f"🚨 Fall detected! Cutting off segment: {fall_segment_id}")
        
        # Complete current segment
        await self._complete_segment()
        
        # Start new segment with FALL_ prefix
        from config import FALL_VIDEO_PREFIX
        self._start_new_segment(prefix=FALL_VIDEO_PREFIX)
        
        return fall_segment_id
    
    async def _create_video(self, video_id: str, frames: List[np.ndarray], recorded_at: datetime) -> Optional[str]:
        """
        Create MP4 video from frames using ffmpeg
        
        Args:
            video_id: Unique video identifier
            frames: List of frame arrays (numpy)
            recorded_at: Recording start timestamp
            
        Returns:
            Path to created video file, or None if failed
        """
        try:
            import ffmpeg
            
            # Output path
            output_path = self.videos_dir / f"{video_id}.mp4"
            
            # Get frame dimensions
            height, width = frames[0].shape[:2]
            
            # Run in thread to not block event loop
            await asyncio.to_thread(
                self._create_video_sync,
                frames,
                str(output_path),
                width,
                height,
                self.video_fps
            )
            
            # Get file size
            file_size = output_path.stat().st_size
            
            # Store in database
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO videos (
                    video_id, local_path, file_size_bytes, duration_sec,
                    frame_count, recorded_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_id,
                str(output_path),
                file_size,
                self.segment_duration,
                len(frames),
                recorded_at.isoformat() + 'Z',
                datetime.now().isoformat() + 'Z'
            ))
            
            conn.commit()
            conn.close()
            
            return str(output_path)
            
        except Exception as e:
            print(f"❌ Error creating video: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_video_sync(self, frames: List[np.ndarray], output_path: str, width: int, height: int, fps: int):
        """Synchronous video creation using ffmpeg (runs in thread)"""
        import ffmpeg
        
        # Create ffmpeg process
        process = (
            ffmpeg
            .input('pipe:', format='rawvideo', pix_fmt='rgb24', s=f'{width}x{height}', r=fps)
            .output(output_path, vcodec='libx264', pix_fmt='yuv420p', preset='medium', crf=23)
            .overwrite_output()
            .run_async(pipe_stdin=True, quiet=True)
        )
        
        # Write frames
        for frame in frames:
            process.stdin.write(frame.tobytes())
        
        process.stdin.close()
        process.wait()
    
    async def _upload_video(self, video_id: str):
        """Upload video to S3 via Lambda API Gateway"""
        print(f"☁️  Uploading video: {video_id}")
        
        try:
            from config import (
                TIMELAPSE_LAMBDA_URL,
                TIMELAPSE_UPLOAD_RETRY_IMMEDIATE,
                USER_ID,
                TIMELAPSE_DEVICE_ID
            )
            
            if not TIMELAPSE_LAMBDA_URL:
                print("⚠️  LAMBDA_API_URL not configured, skipping upload")
                return
            
            # Get video from database
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM videos WHERE video_id = ?', (video_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                print(f"❌ Video not found in database: {video_id}")
                return
            
            columns = [desc[0] for desc in cursor.description]
            video_data = dict(zip(columns, row))
            
            # Retry logic
            for attempt in range(1, TIMELAPSE_UPLOAD_RETRY_IMMEDIATE + 1):
                try:
                    success = await self._upload_attempt(video_data, USER_ID, TIMELAPSE_DEVICE_ID)
                    if success:
                        print(f"✅ Video uploaded successfully: {video_id}")
                        return
                    else:
                        raise Exception("Upload failed")
                        
                except Exception as e:
                    if attempt < TIMELAPSE_UPLOAD_RETRY_IMMEDIATE:
                        backoff = [5, 15, 60][min(attempt-1, 2)]
                        print(f"⚠️  Upload attempt {attempt} failed, retrying in {backoff}s...")
                        await asyncio.sleep(backoff)
                    else:
                        print(f"❌ Upload failed after {TIMELAPSE_UPLOAD_RETRY_IMMEDIATE} attempts: {e}")
                        # Mark for background retry
                        self._update_upload_failure(video_id, str(e))
                        
        except Exception as e:
            print(f"❌ Error uploading video: {e}")
            import traceback
            traceback.print_exc()
    
    async def _upload_attempt(self, video_data: dict, user_id: str, device_id: str) -> bool:
        """Single upload attempt to Lambda/S3"""
        try:
            from config import TIMELAPSE_LAMBDA_URL
            
            video_id = video_data['video_id']
            local_path = video_data['local_path']
            
            # Step 1: Create metadata in DynamoDB via Lambda
            print(f"   Step 1: Creating metadata...")
            metadata_response = await asyncio.to_thread(
                requests.post,
                f"{TIMELAPSE_LAMBDA_URL}/videos",
                params={'userId': user_id},
                json={
                    'videoId': video_id,
                    'title': f"Timelapse {datetime.fromisoformat(video_data['recorded_at'].replace('Z', '')).strftime('%Y-%m-%d %H:%M')}",
                    'recordedAt': video_data['recorded_at'],
                    'durationSec': video_data['duration_sec'],
                    'fileSizeBytes': video_data['file_size_bytes'],
                    'deviceId': device_id,
                    'fileExtension': 'mp4',
                    'mimeType': 'video/mp4'
                },
                timeout=30
            )
            
            if metadata_response.status_code not in [200, 201]:
                raise Exception(f"Metadata creation failed: {metadata_response.status_code} {metadata_response.text}")
            
            metadata = metadata_response.json()
            s3_key = metadata.get('s3Key')
            
            # Step 2: Get pre-signed upload URL
            print(f"   Step 2: Getting upload URL...")
            upload_url_response = await asyncio.to_thread(
                requests.get,
                f"{TIMELAPSE_LAMBDA_URL}/videos/{video_id}/upload-url",
                params={'userId': user_id},
                timeout=30
            )
            
            if upload_url_response.status_code != 200:
                raise Exception(f"Upload URL request failed: {upload_url_response.status_code} - {upload_url_response.text}")
            
            upload_data = upload_url_response.json()
            print(f"   📋 Lambda response: {upload_data}")  # DEBUG
            upload_url = upload_data.get('uploadUrl')
            
            if not upload_url:
                raise Exception(f"No uploadUrl in response. Got keys: {list(upload_data.keys())}")
            
            # Step 3: Upload video to S3
            print(f"   Step 3: Uploading to S3... ({video_data['file_size_bytes']/1024/1024:.1f} MB)")
            with open(local_path, 'rb') as f:
                video_bytes = f.read()
            
            upload_response = await asyncio.to_thread(
                requests.put,
                upload_url,
                data=video_bytes,
                headers={'Content-Type': 'video/mp4'},
                timeout=300  # 5 minutes for large uploads
            )
            
            if upload_response.status_code not in [200, 201, 204]:
                error_body = upload_response.text[:500] if upload_response.text else "No error body"
                raise Exception(f"S3 upload failed: {upload_response.status_code} - {error_body}")
            
            # Update database
            self._update_upload_success(video_id, s3_key)
            
            return True
            
        except Exception as e:
            print(f"   ❌ Upload attempt failed: {e}")
            return False
    
    def _update_upload_success(self, video_id: str, s3_key: str):
        """Update database after successful upload"""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE videos 
            SET uploaded = 1,
                uploaded_at = ?,
                s3_key = ?,
                upload_attempts = upload_attempts + 1,
                last_upload_attempt_at = ?
            WHERE video_id = ?
        ''', (datetime.now().isoformat() + 'Z', s3_key, datetime.now().isoformat() + 'Z', video_id))
        
        conn.commit()
        conn.close()
    
    def _update_upload_failure(self, video_id: str, error_message: str):
        """Update database after upload failure"""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE videos 
            SET upload_attempts = upload_attempts + 1,
                last_upload_attempt_at = ?,
                upload_error = ?
            WHERE video_id = ?
        ''', (datetime.now().isoformat() + 'Z', error_message, video_id))
        
        conn.commit()
        conn.close()
    
    async def _retry_loop(self):
        """Background task to retry failed uploads every hour"""
        print("🔄 Timelapse retry loop started (checks every hour)")
        
        try:
            while self.is_running:
                try:
                    # Wait 1 hour
                    await asyncio.sleep(3600)
                    
                    # Retry failed uploads
                    await self._retry_failed_uploads()
                    
                except Exception as e:
                    print(f"❌ Error in retry loop: {e}")
                    await asyncio.sleep(3600)
        
        except asyncio.CancelledError:
            print("🔄 Timelapse retry loop cancelled")
    
    async def _retry_failed_uploads(self):
        """Retry all failed uploads"""
        from config import TIMELAPSE_UPLOAD_MAX_ATTEMPTS, USER_ID, TIMELAPSE_DEVICE_ID
        
        # Get failed videos
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM videos 
            WHERE uploaded = 0 
            AND upload_attempts < ?
            AND (last_upload_attempt_at IS NULL 
                 OR datetime(last_upload_attempt_at) < datetime('now', '-1 hour'))
        ''', (TIMELAPSE_UPLOAD_MAX_ATTEMPTS,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        if not rows:
            return
        
        print(f"\n🔄 Retrying {len(rows)} failed uploads...")
        
        for row in rows:
            video_data = dict(zip(columns, row))
            video_id = video_data['video_id']
            
            try:
                success = await self._upload_attempt(video_data, USER_ID, TIMELAPSE_DEVICE_ID)
                if success:
                    print(f"✅ Retry successful: {video_id}")
                else:
                    print(f"❌ Retry failed: {video_id}")
            except Exception as e:
                print(f"❌ Retry error for {video_id}: {e}")
    
    async def _cleanup_loop(self):
        """Background task to cleanup old videos daily"""
        print("🔄 Timelapse cleanup loop started (runs daily at 3am)")
        
        try:
            while self.is_running:
                try:
                    # Wait until 3am tomorrow
                    now = datetime.now()
                    tomorrow_3am = (now + timedelta(days=1)).replace(hour=3, minute=0, second=0, microsecond=0)
                    seconds_until_3am = (tomorrow_3am - now).total_seconds()
                    
                    await asyncio.sleep(seconds_until_3am)
                    
                    # Run cleanup
                    await self._cleanup_old_videos()
                    
                except Exception as e:
                    print(f"❌ Error in cleanup loop: {e}")
                    await asyncio.sleep(3600)  # Retry in 1 hour
        
        except asyncio.CancelledError:
            print("🔄 Timelapse cleanup loop cancelled")
    
    async def _cleanup_old_videos(self):
        """Delete videos older than max_age_hours that have been uploaded"""
        print(f"\n🧹 Running cleanup (deleting videos older than {self.max_age_hours}h)...")
        
        cutoff_time = datetime.now() - timedelta(hours=self.max_age_hours)
        
        # Get old uploaded videos
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM videos 
            WHERE uploaded = 1 
            AND datetime(created_at) < ?
            AND deleted_locally = 0
        ''', (cutoff_time.isoformat() + 'Z',))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        deleted_count = 0
        deleted_size = 0
        
        for row in rows:
            video_data = dict(zip(columns, row))
            video_id = video_data['video_id']
            local_path = Path(video_data['local_path'])
            
            try:
                # Delete file
                if local_path.exists():
                    file_size = local_path.stat().st_size
                    local_path.unlink()
                    deleted_size += file_size
                    deleted_count += 1
                    
                    # Mark as deleted in database
                    cursor.execute('''
                        UPDATE videos 
                        SET deleted_locally = 1
                        WHERE video_id = ?
                    ''', (video_id,))
                    
                    print(f"   🗑️  Deleted: {video_id} ({file_size/1024/1024:.1f} MB)")
                    
            except Exception as e:
                print(f"   ❌ Error deleting {video_id}: {e}")
        
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            print(f"✅ Cleanup complete: Deleted {deleted_count} videos ({deleted_size/1024/1024:.1f} MB)")
        else:
            print("✅ Cleanup complete: No videos to delete")
    
    def get_status(self) -> dict:
        """Get timelapse service status"""
        status = {
            'running': self.is_running,
            'recording': self.is_recording,
            'current_segment': {
                'id': self.current_segment_id,
                'frames_captured': self.frames_captured,
                'frames_total': self.frames_per_segment,
                'progress_pct': round(self.frames_captured / self.frames_per_segment * 100, 1) if self.current_segment_id else 0
            }
        }
        
        # Get database stats
        if self.db_path and Path(self.db_path).exists():
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            cursor = conn.cursor()
            
            # Total videos
            cursor.execute('SELECT COUNT(*) FROM videos')
            status['total_videos'] = cursor.fetchone()[0]
            
            # Uploaded videos
            cursor.execute('SELECT COUNT(*) FROM videos WHERE uploaded = 1')
            status['uploaded_videos'] = cursor.fetchone()[0]
            
            # Pending uploads
            cursor.execute('SELECT COUNT(*) FROM videos WHERE uploaded = 0')
            status['pending_uploads'] = cursor.fetchone()[0]
            
            # Storage used
            cursor.execute('SELECT SUM(file_size_bytes) FROM videos WHERE deleted_locally = 0')
            result = cursor.fetchone()[0]
            status['storage_bytes'] = result if result else 0
            status['storage_mb'] = round(status['storage_bytes'] / 1024 / 1024, 1)
            
            conn.close()
        
        return status


# Global service instance
_timelapse_instance: Optional[TimelapseService] = None


def get_timelapse_service() -> TimelapseService:
    """Get the global timelapse service instance"""
    global _timelapse_instance
    if _timelapse_instance is None:
        _timelapse_instance = TimelapseService()
    return _timelapse_instance

