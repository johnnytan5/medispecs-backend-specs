"""
Location Router - Location Tracking API Endpoints
Provides endpoints for starting/stopping location tracking and checking status
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/location", tags=["location"])


@router.post("/start")
async def start_location_tracking():
    """
    Start location tracking service
    
    Begins reading GPS location every 1 second and uploading batches to Lambda every 10 seconds.
    """
    try:
        from services.location_service import get_location_service
        
        location_service = get_location_service()
        
        if location_service.is_running:
            return {
                "status": "already_running",
                "message": "Location tracking is already running"
            }
        
        await location_service.start()
        
        return {
            "status": "started",
            "message": "Location tracking started successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting location tracking: {str(e)}")


@router.post("/stop")
async def stop_location_tracking():
    """
    Stop location tracking service
    
    Stops reading GPS and uploads any remaining buffered locations.
    """
    try:
        from services.location_service import get_location_service
        
        location_service = get_location_service()
        
        if not location_service.is_running:
            return {
                "status": "not_running",
                "message": "Location tracking is not running"
            }
        
        await location_service.stop()
        
        return {
            "status": "stopped",
            "message": "Location tracking stopped successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping location tracking: {str(e)}")


@router.get("/status")
async def get_location_status():
    """
    Get location tracking service status
    
    Returns current status including:
    - Running state
    - GPS fix status
    - Current location (if available)
    - Buffer size
    - Statistics (locations read, sent, errors)
    """
    try:
        from services.location_service import get_location_service
        
        location_service = get_location_service()
        status = location_service.get_status()
        
        return {
            "status": "success",
            **status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting location status: {str(e)}")


@router.get("/current")
async def get_current_location():
    """
    Get current GPS location (if available)
    
    Returns the most recent GPS location reading.
    """
    try:
        from services.location_service import get_location_service
        
        location_service = get_location_service()
        
        if not location_service.current_location:
            return {
                "status": "no_fix",
                "message": "No GPS fix available",
                "has_fix": False
            }
        
        return {
            "status": "success",
            "has_fix": location_service.has_fix,
            "location": location_service.current_location,
            "last_fix_time": location_service.last_fix_time.isoformat() if location_service.last_fix_time else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting current location: {str(e)}")

