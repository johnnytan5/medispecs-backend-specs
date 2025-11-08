"""
Speech-to-Text API Router
Provides endpoints for voice command functionality
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional


router = APIRouter(prefix="/stt", tags=["speech-to-text"])


class TestListenRequest(BaseModel):
    """Request model for test listening"""
    duration: int = 5  # Recording duration in seconds
    
    class Config:
        json_schema_extra = {
            "example": {
                "duration": 5
            }
        }


@router.get("/status")
async def get_stt_status():
    """
    Get STT service status
    
    Returns information about the speech-to-text service including:
    - Initialization status
    - Listening status
    - Wake word configuration
    - Audio device settings
    """
    try:
        from services.stt_service import get_stt_service
        
        stt = get_stt_service()
        status = stt.get_status()
        
        return {
            "status": "available" if status['initialized'] else "not_initialized",
            **status
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "STT service not available"
        }


@router.get("/devices")
async def list_audio_devices():
    """
    List all available audio input devices
    
    Returns a list of audio devices that can be used for speech input.
    Useful for selecting the correct USB microphone.
    """
    try:
        from services.stt_service import get_stt_service
        
        stt = get_stt_service()
        devices = stt.list_audio_devices()
        
        # Format device list
        device_list = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:  # Only input devices
                device_list.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                })
        
        return {
            "status": "success",
            "count": len(device_list),
            "devices": device_list
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing devices: {str(e)}")


@router.post("/test")
async def test_listen(request: TestListenRequest):
    """
    Test STT by recording and transcribing audio
    
    Records audio for the specified duration and returns the transcribed text.
    Useful for testing microphone and speech recognition accuracy.
    
    - **duration**: Recording duration in seconds (default: 5)
    """
    try:
        from services.stt_service import get_stt_service
        
        stt = get_stt_service()
        
        if not stt.get_status()['initialized']:
            raise HTTPException(
                status_code=503,
                detail="STT service not initialized. Check if Vosk model is loaded."
            )
        
        # Record and transcribe
        text = await stt.test_listen(duration=request.duration)
        
        return {
            "status": "success",
            "transcribed_text": text,
            "duration": request.duration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test recording failed: {str(e)}")


@router.post("/start")
async def start_listening():
    """
    Start continuous wake word detection
    
    Starts the STT service to continuously listen for the wake word.
    Once started, the service will listen in the background.
    """
    try:
        from services.stt_service import get_stt_service
        
        stt = get_stt_service()
        
        if not stt.get_status()['initialized']:
            raise HTTPException(
                status_code=503,
                detail="STT service not initialized"
            )
        
        if stt.is_running:
            return {
                "status": "already_running",
                "message": "STT service is already listening"
            }
        
        await stt.start()
        
        return {
            "status": "success",
            "message": "STT service started - listening for wake word",
            "wake_word": stt.wake_word
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start STT: {str(e)}")


@router.post("/stop")
async def stop_listening():
    """
    Stop continuous wake word detection
    
    Stops the STT service background listening.
    """
    try:
        from services.stt_service import get_stt_service
        
        stt = get_stt_service()
        
        if not stt.is_running:
            return {
                "status": "not_running",
                "message": "STT service is not running"
            }
        
        await stt.stop()
        
        return {
            "status": "success",
            "message": "STT service stopped"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop STT: {str(e)}")


# Placeholder for future OpenAI LLM integration
@router.post("/command")
async def process_command_with_llm():
    """
    Process voice command with LLM (Future Implementation)
    
    This endpoint is a placeholder for future OpenAI LLM integration.
    Will process transcribed commands and return intelligent responses.
    
    Future flow:
    1. Wake word detected
    2. Command transcribed
    3. Sent to OpenAI LLM
    4. Response generated
    5. TTS speaks response
    """
    return {
        "status": "not_implemented",
        "message": "LLM integration coming soon",
        "note": "Currently, transcribed commands are logged. LLM processing will be added next."
    }

