"""
Timelapse API Router
Provides endpoints for timelapse recording control and video management
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import sqlite3


router = APIRouter(prefix="/timelapse", tags=["timelapse"])


@router.get("/status")
async def get_status():
    """
    Get timelapse service status
    
    Returns current recording status, progress, and statistics.
    """
    try:
        from services.timelapse_service import get_timelapse_service
        
        timelapse = get_timelapse_service()
        status = timelapse.get_status()
        
        return {
            "status": "success",
            **status
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/start")
async def start_recording():
    """
    Start timelapse recording
    
    Begins capturing frames and creating video segments.
    """
    try:
        from services.timelapse_service import get_timelapse_service
        
        timelapse = get_timelapse_service()
        
        if timelapse.is_running:
            return {
                "status": "already_running",
                "message": "Timelapse is already recording"
            }
        
        await timelapse.start()
        
        return {
            "status": "success",
            "message": "Timelapse recording started"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_recording():
    """
    Stop timelapse recording
    
    Stops capturing frames. Current segment will be completed.
    """
    try:
        from services.timelapse_service import get_timelapse_service
        
        timelapse = get_timelapse_service()
        
        if not timelapse.is_running:
            return {
                "status": "not_running",
                "message": "Timelapse is not recording"
            }
        
        await timelapse.stop()
        
        return {
            "status": "success",
            "message": "Timelapse recording stopped"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete-segment")
async def complete_current_segment():
    """
    Manually complete the current video segment
    
    Forces the current segment to finish and create a video,
    even if it hasn't reached the full 450 frames yet.
    
    Useful for:
    - Testing without waiting 15 minutes
    - Creating segments at specific moments
    - Ending a segment early if needed
    """
    try:
        from services.timelapse_service import get_timelapse_service
        
        timelapse = get_timelapse_service()
        
        if not timelapse.is_recording:
            return {
                "status": "not_recording",
                "message": "Timelapse is not recording"
            }
        
        if not timelapse.current_segment_id:
            return {
                "status": "no_segment",
                "message": "No active segment to complete"
            }
        
        # Check if there are frames to save
        if timelapse.frames_captured == 0:
            return {
                "status": "no_frames",
                "message": "No frames captured yet in current segment"
            }
        
        segment_id = timelapse.current_segment_id
        frames_captured = timelapse.frames_captured
        
        # Force complete the segment
        await timelapse._complete_segment()
        
        return {
            "status": "success",
            "message": f"Segment {segment_id} completed manually",
            "segment_id": segment_id,
            "frames_captured": frames_captured,
            "note": "Video created with available frames, new segment started"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/videos")
async def list_videos():
    """
    List all timelapse videos
    
    Returns list of all videos with metadata and upload status.
    """
    try:
        from services.timelapse_service import get_timelapse_service
        
        timelapse = get_timelapse_service()
        
        if not timelapse.db_path or not Path(timelapse.db_path).exists():
            return {
                "status": "success",
                "videos": []
            }
        
        conn = sqlite3.connect(str(timelapse.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT video_id, local_path, s3_key, file_size_bytes,
                   duration_sec, frame_count, recorded_at, created_at,
                   uploaded_at, uploaded, upload_attempts, deleted_locally
            FROM videos 
            ORDER BY created_at DESC
            LIMIT 100
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        videos = []
        for row in rows:
            videos.append({
                'video_id': row[0],
                'local_path': row[1],
                's3_key': row[2],
                'file_size_bytes': row[3],
                'file_size_mb': round(row[3] / 1024 / 1024, 1) if row[3] else 0,
                'duration_sec': row[4],
                'frame_count': row[5],
                'recorded_at': row[6],
                'created_at': row[7],
                'uploaded_at': row[8],
                'uploaded': bool(row[9]),
                'upload_attempts': row[10],
                'deleted_locally': bool(row[11]),
                'exists': Path(row[1]).exists() if row[1] else False
            })
        
        return {
            "status": "success",
            "count": len(videos),
            "videos": videos
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/videos/{video_id}")
async def get_video(video_id: str):
    """
    Get specific video details
    
    Returns metadata for a single video.
    """
    try:
        from services.timelapse_service import get_timelapse_service
        
        timelapse = get_timelapse_service()
        
        if not timelapse.db_path or not Path(timelapse.db_path).exists():
            raise HTTPException(status_code=404, detail="Video not found")
        
        conn = sqlite3.connect(str(timelapse.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT video_id, local_path, s3_key, file_size_bytes,
                   duration_sec, frame_count, recorded_at, created_at,
                   uploaded_at, uploaded, upload_attempts, upload_error,
                   deleted_locally
            FROM videos 
            WHERE video_id = ?
        ''', (video_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        
        return {
            "status": "success",
            "video": {
                'video_id': row[0],
                'local_path': row[1],
                's3_key': row[2],
                'file_size_bytes': row[3],
                'file_size_mb': round(row[3] / 1024 / 1024, 1) if row[3] else 0,
                'duration_sec': row[4],
                'frame_count': row[5],
                'recorded_at': row[6],
                'created_at': row[7],
                'uploaded_at': row[8],
                'uploaded': bool(row[9]),
                'upload_attempts': row[10],
                'upload_error': row[11],
                'deleted_locally': bool(row[12]),
                'exists': Path(row[1]).exists() if row[1] else False
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/videos/{video_id}/stream")
async def stream_video(video_id: str):
    """
    Stream/download video file
    
    Returns the actual MP4 video file.
    """
    try:
        from services.timelapse_service import get_timelapse_service
        
        timelapse = get_timelapse_service()
        
        if not timelapse.db_path or not Path(timelapse.db_path).exists():
            raise HTTPException(status_code=404, detail="Video not found")
        
        conn = sqlite3.connect(str(timelapse.db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT local_path FROM videos WHERE video_id = ?', (video_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        
        video_path = Path(row[0])
        
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found on disk")
        
        return FileResponse(
            path=str(video_path),
            media_type="video/mp4",
            filename=f"{video_id}.mp4"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending-uploads")
async def list_pending_uploads():
    """
    List videos pending upload
    
    Returns videos that have not been successfully uploaded yet.
    """
    try:
        from services.timelapse_service import get_timelapse_service
        
        timelapse = get_timelapse_service()
        
        if not timelapse.db_path or not Path(timelapse.db_path).exists():
            return {
                "status": "success",
                "videos": []
            }
        
        conn = sqlite3.connect(str(timelapse.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT video_id, local_path, file_size_bytes, recorded_at,
                   created_at, upload_attempts, last_upload_attempt_at, upload_error
            FROM videos 
            WHERE uploaded = 0
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        videos = []
        for row in rows:
            videos.append({
                'video_id': row[0],
                'local_path': row[1],
                'file_size_mb': round(row[2] / 1024 / 1024, 1) if row[2] else 0,
                'recorded_at': row[3],
                'created_at': row[4],
                'upload_attempts': row[5],
                'last_upload_attempt_at': row[6],
                'upload_error': row[7]
            })
        
        return {
            "status": "success",
            "count": len(videos),
            "videos": videos
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry-upload/{video_id}")
async def retry_upload(video_id: str):
    """
    Manually retry uploading a specific video
    
    Attempts to upload a video that previously failed.
    """
    try:
        from services.timelapse_service import get_timelapse_service
        
        timelapse = get_timelapse_service()
        await timelapse._upload_video(video_id)
        
        return {
            "status": "success",
            "message": f"Upload retry initiated for {video_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry-all")
async def retry_all_uploads():
    """
    Retry all failed uploads
    
    Attempts to upload all videos that previously failed.
    """
    try:
        from services.timelapse_service import get_timelapse_service
        
        timelapse = get_timelapse_service()
        await timelapse._retry_failed_uploads()
        
        return {
            "status": "success",
            "message": "Retry initiated for all failed uploads"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def manual_cleanup():
    """
    Manually trigger cleanup of old videos
    
    Deletes videos older than configured age that have been uploaded.
    """
    try:
        from services.timelapse_service import get_timelapse_service
        
        timelapse = get_timelapse_service()
        await timelapse._cleanup_old_videos()
        
        return {
            "status": "success",
            "message": "Cleanup completed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/videos/{video_id}")
async def delete_video(video_id: str):
    """
    Delete a specific video
    
    Deletes the video file from disk and updates database.
    """
    try:
        from services.timelapse_service import get_timelapse_service
        
        timelapse = get_timelapse_service()
        
        if not timelapse.db_path or not Path(timelapse.db_path).exists():
            raise HTTPException(status_code=404, detail="Video not found")
        
        conn = sqlite3.connect(str(timelapse.db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT local_path FROM videos WHERE video_id = ?', (video_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Video not found")
        
        video_path = Path(row[0])
        
        # Delete file if exists
        if video_path.exists():
            video_path.unlink()
        
        # Update database
        cursor.execute('''
            UPDATE videos 
            SET deleted_locally = 1
            WHERE video_id = ?
        ''', (video_id,))
        
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "message": f"Video {video_id} deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_statistics():
    """
    Get timelapse statistics
    
    Returns detailed statistics about storage, uploads, and recordings.
    """
    try:
        from services.timelapse_service import get_timelapse_service
        
        timelapse = get_timelapse_service()
        
        stats = {
            'recording': timelapse.is_recording,
            'current_segment': timelapse.get_status()['current_segment']
        }
        
        if timelapse.db_path and Path(timelapse.db_path).exists():
            conn = sqlite3.connect(str(timelapse.db_path))
            cursor = conn.cursor()
            
            # Total statistics
            cursor.execute('SELECT COUNT(*), SUM(file_size_bytes) FROM videos')
            row = cursor.fetchone()
            stats['total_videos'] = row[0] or 0
            stats['total_size_bytes'] = row[1] or 0
            stats['total_size_mb'] = round(stats['total_size_bytes'] / 1024 / 1024, 1)
            
            # Upload statistics
            cursor.execute('SELECT COUNT(*) FROM videos WHERE uploaded = 1')
            stats['uploaded_videos'] = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT COUNT(*) FROM videos WHERE uploaded = 0')
            stats['pending_videos'] = cursor.fetchone()[0] or 0
            
            # Local storage (not deleted)
            cursor.execute('SELECT COUNT(*), SUM(file_size_bytes) FROM videos WHERE deleted_locally = 0')
            row = cursor.fetchone()
            stats['local_videos'] = row[0] or 0
            stats['local_size_bytes'] = row[1] or 0
            stats['local_size_mb'] = round(stats['local_size_bytes'] / 1024 / 1024, 1)
            
            conn.close()
        
        return {
            "status": "success",
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

