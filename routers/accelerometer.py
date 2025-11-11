"""
Accelerometer Router - Fall Detection & Emergency Status Endpoints
Provides endpoints for monitoring accelerometer and polling emergency status
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter(prefix="/accelerometer", tags=["accelerometer"])


class AccelerometerStatus(BaseModel):
    """Current accelerometer status"""
    monitoring: bool
    current_state: str
    current_readings: Optional[Dict[str, Any]]


class EmergencyStatus(BaseModel):
    """Emergency status for caregiver polling"""
    monitoring: bool
    current_state: str
    latest_fall: Optional[Dict[str, Any]]
    current_readings: Optional[Dict[str, Any]]


class FallAcknowledgement(BaseModel):
    """Acknowledge a fall event"""
    user_confirmed: bool
    response_text: Optional[str] = None


@router.get("/status", response_model=AccelerometerStatus)
async def get_accelerometer_status():
    """
    Get current accelerometer status and readings
    
    Returns:
        - monitoring: Whether fall detection is active
        - current_state: Current state (idle, free_fall, impact, inactivity, cooldown)
        - current_readings: Current acceleration values (x, y, z, total)
    """
    try:
        from services.accelerometer_service import get_accelerometer_service
        
        accel = get_accelerometer_service()
        readings = accel.get_current_readings()
        
        return {
            "monitoring": accel.is_running,
            "current_state": accel.state.value,
            "current_readings": readings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emergency/status", response_model=EmergencyStatus)
async def get_emergency_status():
    """
    Get emergency status for caregiver polling
    
    **This endpoint is designed to be polled every 5 seconds by caregiver devices**
    
    Returns:
        - monitoring: Whether fall detection is active
        - current_state: Current detection state
        - latest_fall: Most recent fall event (if any)
            - timestamp: When fall was detected
            - freefall_g: Free fall acceleration magnitude
            - impact_g: Impact acceleration magnitude
            - inactivity_sec: Duration of inactivity
            - user_response: "CONFIRMED" | "NO_RESPONSE" | null (pending)
            - acknowledged: Whether fall has been handled
        - current_readings: Current sensor readings
    
    Example usage (caregiver app polls this every 5s):
        ```
        GET /accelerometer/emergency/status
        
        Response:
        {
          "monitoring": true,
          "current_state": "idle",
          "latest_fall": {
            "timestamp": "2025-11-11T20:15:30.123456Z",
            "freefall_g": 0.35,
            "impact_g": 2.8,
            "inactivity_sec": 5.2,
            "user_response": "NO_RESPONSE",
            "acknowledged": true
          },
          "current_readings": {...}
        }
        ```
    """
    try:
        from services.accelerometer_service import get_accelerometer_service
        
        accel = get_accelerometer_service()
        emergency_status = accel.get_emergency_status()
        
        return emergency_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_monitoring():
    """
    Start fall detection monitoring
    
    Begins continuous sampling from MPU6050 at configured rate (default 50Hz)
    """
    try:
        from services.accelerometer_service import get_accelerometer_service
        
        accel = get_accelerometer_service()
        
        if accel.is_running:
            return {"status": "already_running", "message": "Fall detection is already active"}
        
        await accel.start()
        
        return {
            "status": "started",
            "message": "Fall detection monitoring started",
            "sampling_rate_hz": accel.sampling_rate
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_monitoring():
    """
    Stop fall detection monitoring
    """
    try:
        from services.accelerometer_service import get_accelerometer_service
        
        accel = get_accelerometer_service()
        
        if not accel.is_running:
            return {"status": "not_running", "message": "Fall detection is not active"}
        
        await accel.stop()
        
        return {
            "status": "stopped",
            "message": "Fall detection monitoring stopped"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-fall")
async def test_fall_detection():
    """
    Simulate a fall for testing purposes
    
    Triggers the fall detection callback without actual sensor readings.
    Useful for testing TTS alerts, video cutoff, and emergency notifications.
    """
    try:
        from services.accelerometer_service import get_accelerometer_service
        
        accel = get_accelerometer_service()
        
        if not accel.is_running:
            return {
                "status": "not_running",
                "message": "Fall detection must be running to simulate falls. Call POST /accelerometer/start first"
            }
        
        await accel.simulate_fall()
        
        return {
            "status": "simulated",
            "message": "Fall simulation triggered",
            "event": accel.latest_fall_event
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/acknowledge")
async def acknowledge_fall(ack: FallAcknowledgement):
    """
    Acknowledge a fall event (typically called by STT service after user confirmation)
    
    Body:
        - user_confirmed: true if user said "okay", false if timeout
        - response_text: What the user actually said (optional)
    """
    try:
        from services.accelerometer_service import get_accelerometer_service
        
        accel = get_accelerometer_service()
        
        if not accel.latest_fall_event:
            return {
                "status": "no_fall",
                "message": "No fall event to acknowledge"
            }
        
        accel.acknowledge_fall(ack.user_confirmed, ack.response_text)
        
        return {
            "status": "acknowledged",
            "message": f"Fall acknowledged: {accel.latest_fall_event['user_response']}",
            "event": accel.latest_fall_event
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/readings")
async def get_current_readings():
    """
    Get current accelerometer readings
    
    Returns raw acceleration values and calculated total magnitude
    """
    try:
        from services.accelerometer_service import get_accelerometer_service
        
        accel = get_accelerometer_service()
        
        if not accel.is_running:
            raise HTTPException(status_code=400, detail="Accelerometer is not running")
        
        return accel.get_current_readings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

