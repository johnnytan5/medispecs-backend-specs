"""
Text-to-Speech API Router
Provides endpoints for testing and controlling TTS functionality
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional


router = APIRouter(prefix="/tts", tags=["text-to-speech"])


class SpeakRequest(BaseModel):
    """Request model for speaking text"""
    text: str = Field(..., description="Text to speak", min_length=1, max_length=500)
    rate: Optional[int] = Field(None, description="Speech rate in WPM (50-300)", ge=50, le=300)
    volume: Optional[float] = Field(None, description="Volume level (0.0-1.0)", ge=0.0, le=1.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Hello! This is a test of the text to speech system.",
                "rate": 130,
                "volume": 0.9
            }
        }


@router.post("/speak")
async def speak_text(request: SpeakRequest):
    """
    Speak text using TTS
    
    This endpoint converts text to speech and plays it through the audio output.
    Useful for testing TTS functionality.
    
    - **text**: Text to speak (1-500 characters)
    - **rate**: Optional speech rate in words per minute (50-300, default: 130)
    - **volume**: Optional volume level (0.0-1.0, default: 0.9)
    """
    try:
        from services.tts_service import get_tts_service
        
        tts = get_tts_service()
        
        if not tts.is_available:
            raise HTTPException(
                status_code=503,
                detail="TTS service not available. Check if pyttsx3 is installed and audio output is configured."
            )
        
        # Speak asynchronously (non-blocking)
        await tts.speak_async(request.text, rate=request.rate, volume=request.volume)
        
        return {
            "status": "success",
            "message": "Text spoken successfully",
            "text": request.text,
            "engine": "pyttsx3",
            "rate": request.rate or tts.default_rate,
            "volume": request.volume or tts.default_volume
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


@router.get("/status")
async def get_tts_status():
    """
    Get TTS service status and configuration
    
    Returns information about the TTS service including:
    - Availability status
    - Current engine (pyttsx3)
    - Speech rate and volume settings
    - Current voice
    - Number of available voices
    """
    try:
        from services.tts_service import get_tts_service
        
        tts = get_tts_service()
        info = tts.get_info()
        
        return {
            "status": "available" if info.get('available') else "unavailable",
            **info
        }
        
    except Exception as e:
        return {
            "status": "error",
            "available": False,
            "error": str(e),
            "message": "TTS service initialization failed"
        }


@router.get("/voices")
async def list_voices():
    """
    List all available TTS voices
    
    Returns a list of voices that can be used with the TTS system.
    Each voice includes:
    - **id**: Voice identifier (use with set_voice)
    - **name**: Human-readable voice name
    - **languages**: Supported languages (if available)
    """
    try:
        from services.tts_service import get_tts_service
        
        tts = get_tts_service()
        
        if not tts.is_available:
            raise HTTPException(
                status_code=503,
                detail="TTS service not available"
            )
        
        voices = tts.list_voices()
        
        return {
            "status": "success",
            "count": len(voices),
            "voices": voices
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing voices: {str(e)}")


@router.post("/voice/{voice_id}")
async def set_voice(voice_id: str):
    """
    Set the TTS voice
    
    Changes the voice used for speech synthesis.
    Get available voice IDs from the /tts/voices endpoint.
    
    - **voice_id**: Voice identifier from the voices list
    """
    try:
        from services.tts_service import get_tts_service
        
        tts = get_tts_service()
        
        if not tts.is_available:
            raise HTTPException(
                status_code=503,
                detail="TTS service not available"
            )
        
        success = tts.set_voice(voice_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Voice changed to {voice_id}",
                "voice_id": voice_id
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to set voice")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting voice: {str(e)}")


@router.post("/rate/{rate}")
async def set_speech_rate(rate: int):
    """
    Set the speech rate
    
    Adjusts how fast the TTS speaks.
    
    - **rate**: Words per minute (50-300)
        - 50-100: Very slow
        - 100-130: Slow (good for seniors)
        - 130-150: Normal
        - 150-200: Fast
        - 200-300: Very fast
    """
    if rate < 50 or rate > 300:
        raise HTTPException(
            status_code=400,
            detail="Rate must be between 50 and 300 WPM"
        )
    
    try:
        from services.tts_service import get_tts_service
        
        tts = get_tts_service()
        
        if not tts.is_available:
            raise HTTPException(
                status_code=503,
                detail="TTS service not available"
            )
        
        tts.set_rate(rate)
        
        return {
            "status": "success",
            "message": f"Speech rate set to {rate} WPM",
            "rate": rate
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting rate: {str(e)}")


@router.post("/volume/{volume}")
async def set_volume(volume: float):
    """
    Set the volume level
    
    Adjusts the TTS output volume.
    
    - **volume**: Volume level (0.0-1.0)
        - 0.0: Muted
        - 0.5: Half volume
        - 1.0: Full volume
    """
    if volume < 0.0 or volume > 1.0:
        raise HTTPException(
            status_code=400,
            detail="Volume must be between 0.0 and 1.0"
        )
    
    try:
        from services.tts_service import get_tts_service
        
        tts = get_tts_service()
        
        if not tts.is_available:
            raise HTTPException(
                status_code=503,
                detail="TTS service not available"
            )
        
        tts.set_volume(volume)
        
        return {
            "status": "success",
            "message": f"Volume set to {volume}",
            "volume": volume
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting volume: {str(e)}")


@router.post("/stop")
async def stop_speech():
    """
    Stop current speech
    
    Immediately stops any ongoing speech output.
    """
    try:
        from services.tts_service import get_tts_service
        
        tts = get_tts_service()
        
        if not tts.is_available:
            raise HTTPException(
                status_code=503,
                detail="TTS service not available"
            )
        
        tts.stop()
        
        return {
            "status": "success",
            "message": "Speech stopped"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping speech: {str(e)}")

