from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import asyncio

router = APIRouter(prefix="/display", tags=["display"])


class DisplayRequest(BaseModel):
    message: str
    font_size: Optional[int] = 14
    should_blink: Optional[bool] = True
    display_time: Optional[int] = 10


class DisplayAndSpeakRequest(BaseModel):
    """Request model for displaying on OLED and speaking via TTS simultaneously"""
    message: str = Field(..., description="Message to display on OLED and speak via TTS")
    font_size: Optional[int] = Field(14, description="OLED font size")
    should_blink: Optional[bool] = Field(True, description="Whether OLED message should blink")
    display_time: Optional[int] = Field(10, description="How long to display on OLED (seconds)")
    tts_text: Optional[str] = Field(None, description="Text to speak (if different from message, otherwise uses message)")
    tts_rate: Optional[int] = Field(None, description="TTS speech rate in WPM (50-300)", ge=50, le=300)
    tts_volume: Optional[float] = Field(None, description="TTS volume level (0.0-1.0)", ge=0.0, le=1.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Time to take your medication",
                "font_size": 14,
                "should_blink": True,
                "display_time": 10,
                "tts_text": "Time to take your medication",
                "tts_rate": 130,
                "tts_volume": 0.9
            }
        }


@router.post("/show")
async def show_on_display(request: DisplayRequest):
    """
    Display a message on the OLED screen.
    Useful for testing or triggering custom displays.
    """
    try:
        from services.oled_display import get_oled_service
        oled = get_oled_service()
        
        print(f"\n{'='*60}")
        print(f"📺 DISPLAY REQUEST: {request.message}")
        print(f"   Font Size: {request.font_size}")
        print(f"   Blink: {request.should_blink}")
        print(f"   Duration: {request.display_time}s")
        print(f"{'='*60}\n")
        
        if not oled.is_available:
            print("⚠️  OLED hardware not available - message shown above")
            return {
                "status": "warning",
                "message": "OLED display not available",
                "would_display": request.message
            }
        
        oled.display_reminder(
            message=request.message,
            font_size=request.font_size,
            should_blink=request.should_blink,
            display_time=request.display_time
        )
        
        return {
            "status": "success",
            "message": "Message displayed on OLED",
            "displayed": request.message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error displaying message: {str(e)}")


@router.post("/show-and-speak")
async def show_and_speak(request: DisplayAndSpeakRequest):
    """
    Display a message on the OLED screen AND speak it via TTS simultaneously.
    
    This endpoint combines both display and TTS functionality in a single call.
    The OLED display and TTS will run in parallel (simultaneously).
    
    - **message**: Message to display on OLED
    - **tts_text**: Text to speak (optional, defaults to message if not provided)
    - **font_size**: OLED font size (default: 14)
    - **should_blink**: Whether OLED message should blink (default: True)
    - **display_time**: How long to display on OLED in seconds (default: 10)
    - **tts_rate**: TTS speech rate in words per minute (50-300, optional)
    - **tts_volume**: TTS volume level (0.0-1.0, optional)
    """
    try:
        from services.oled_display import get_oled_service
        from services.tts_service import get_tts_service
        
        oled = get_oled_service()
        tts = get_tts_service()
        
        # Determine TTS text (use tts_text if provided, otherwise use message)
        tts_text = request.tts_text if request.tts_text is not None else request.message
        
        print(f"\n{'='*60}")
        print(f"📺 DISPLAY + 🔊 TTS REQUEST")
        print(f"   OLED Message: {request.message}")
        print(f"   TTS Text: {tts_text}")
        print(f"   Font Size: {request.font_size}")
        print(f"   Blink: {request.should_blink}")
        print(f"   Display Duration: {request.display_time}s")
        if request.tts_rate:
            print(f"   TTS Rate: {request.tts_rate} WPM")
        if request.tts_volume:
            print(f"   TTS Volume: {request.tts_volume}")
        print(f"{'='*60}\n")
        
        # Check availability
        oled_available = oled.is_available
        tts_available = tts.is_available
        
        if not oled_available and not tts_available:
            return {
                "status": "warning",
                "message": "Neither OLED display nor TTS service is available",
                "oled_available": False,
                "tts_available": False
            }
        
        # Run OLED and TTS simultaneously (in parallel)
        tasks = []
        
        # OLED task (synchronous, run in thread pool)
        if oled_available:
            oled_task = asyncio.create_task(
                asyncio.to_thread(
                    oled.display_reminder,
                    message=request.message,
                    font_size=request.font_size,
                    should_blink=request.should_blink,
                    display_time=request.display_time
                )
            )
            tasks.append(oled_task)
        else:
            print("⚠️  OLED hardware not available")
        
        # TTS task (async)
        if tts_available:
            tts_task = asyncio.create_task(
                tts.speak_async(
                    tts_text,
                    rate=request.tts_rate,
                    volume=request.tts_volume
                )
            )
            tasks.append(tts_task)
        else:
            print("⚠️  TTS service not available")
        
        # Wait for both to complete
        if tasks:
            await asyncio.gather(*tasks)
        
        return {
            "status": "success",
            "message": "Message displayed and spoken",
            "oled": {
                "available": oled_available,
                "displayed": request.message if oled_available else None
            },
            "tts": {
                "available": tts_available,
                "spoken": tts_text if tts_available else None
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error displaying and speaking: {str(e)}")


@router.post("/clear")
async def clear_display():
    """Clear the OLED display"""
    try:
        from services.oled_display import get_oled_service
        oled = get_oled_service()
        
        if not oled.is_available:
            return {
                "status": "warning",
                "message": "OLED display not available"
            }
        
        oled.clear_display()
        
        return {
            "status": "success",
            "message": "Display cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing display: {str(e)}")


@router.get("/status")
async def display_status():
    """Check OLED display status"""
    try:
        from services.oled_display import get_oled_service
        oled = get_oled_service()
        
        return {
            "status": "available" if oled.is_available else "unavailable",
            "device_initialized": oled.is_available
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/printtimenow")
async def print_time_now():
    """Display the current time on the OLED screen"""
    try:
        from services.oled_display import get_oled_service
        oled = get_oled_service()
        
        # Get current time
        now = datetime.now()
        time_string = now.strftime("%I:%M %p")  # Format: 08:30 PM
        date_string = now.strftime("%Y-%m-%d")  # Format: 2024-11-07
        
        # Combine for display
        display_message = f"{time_string}\n{date_string}"
        
        print(f"\n{'='*60}")
        print(f"📺 DISPLAY REQUEST: Show current time")
        print(f"   Time: {time_string}")
        print(f"   Date: {date_string}")
        print(f"{'='*60}\n")
        
        if not oled.is_available:
            print("⚠️  OLED hardware not available - message shown above")
            return {
                "status": "warning",
                "message": "OLED display not available",
                "current_time": time_string,
                "current_date": date_string
            }
        
        # Display on OLED
        oled.display_reminder(
            message=display_message,
            font_size=16,
            should_blink=False,
            display_time=5
        )
        
        return {
            "status": "success",
            "message": "Current time displayed on OLED",
            "time": time_string,
            "date": date_string,
            "timestamp": now.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error displaying time: {str(e)}")

