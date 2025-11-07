from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/display", tags=["display"])


class DisplayRequest(BaseModel):
    message: str
    font_size: Optional[int] = 14
    should_blink: Optional[bool] = True
    display_time: Optional[int] = 10


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

