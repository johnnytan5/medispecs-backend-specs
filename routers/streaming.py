"""
Live Video Streaming Router - MJPEG stream from camera

This router provides a live video stream endpoint that shares frames
from the face detection service's camera without interfering with
face detection operations.
"""

import cv2
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse


router = APIRouter(prefix="/stream", tags=["streaming"])


async def generate_frames():
    """
    Generate MJPEG frames from the face detection service's camera.
    
    This function reads frames from the shared frame buffer maintained
    by the FaceDetectionService, ensuring no camera access conflicts.
    
    Yields:
        bytes: MJPEG frame data in multipart format
    """
    from services.face_detection_service import get_face_detection_service
    
    face_service = get_face_detection_service()
    
    # Wait for camera to be ready (up to 30 seconds)
    wait_count = 0
    while not face_service.is_running and wait_count < 60:
        await asyncio.sleep(0.5)
        wait_count += 1
    
    if not face_service.is_running:
        # If camera still not ready, yield error frame
        error_message = "Camera not available"
        print(f"⚠️  {error_message}")
        return
    
    print("📹 Starting MJPEG stream...")
    frame_count = 0
    
    try:
        while face_service.is_running:
            # Get latest frame from shared buffer
            async with face_service.frame_lock:
                if face_service.latest_frame is not None:
                    frame = face_service.latest_frame.copy()
                else:
                    # No frame available yet, wait
                    await asyncio.sleep(0.1)
                    continue
            
            # Convert RGB to BGR for JPEG encoding (OpenCV expects BGR)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Encode frame as JPEG with quality 80 (balance between quality and bandwidth)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            _, buffer = cv2.imencode('.jpg', frame_bgr, encode_param)
            frame_bytes = buffer.tobytes()
            
            # Yield frame in MJPEG format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            frame_count += 1
            if frame_count % 100 == 0:
                print(f"📹 Streamed {frame_count} frames...")
            
            # Control frame rate: 15 FPS (smooth enough, bandwidth-efficient)
            await asyncio.sleep(1/15)
            
    except GeneratorExit:
        print(f"📹 Stream closed by client (streamed {frame_count} frames)")
    except Exception as e:
        print(f"❌ Error in stream: {e}")
        import traceback
        traceback.print_exc()


@router.get("/live")
async def video_stream():
    """
    Live MJPEG video stream endpoint.
    
    This endpoint streams live video from the camera in MJPEG format,
    which can be viewed directly in web browsers.
    
    Usage:
        1. Start the FastAPI server
        2. Access via browser: http://your-server:8000/stream/live
        3. Or via ngrok: https://your-ngrok-url.ngrok.io/stream/live
    
    Returns:
        StreamingResponse: Continuous MJPEG stream
    """
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/status")
async def stream_status():
    """
    Get streaming status and camera information.
    
    Returns:
        dict: Status information including camera state
    """
    from services.face_detection_service import get_face_detection_service
    
    face_service = get_face_detection_service()
    
    return {
        "status": "available" if face_service.is_running else "unavailable",
        "camera_running": face_service.is_running,
        "camera_type": "picamera2" if face_service.use_picamera else "opencv",
        "has_frame": face_service.latest_frame is not None,
        "stream_url": "/stream/live",
        "message": "Camera is ready for streaming" if face_service.is_running else "Camera not initialized"
    }

