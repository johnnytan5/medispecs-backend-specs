"""
Medications Router - Medication Management & Webhook Endpoints
Provides endpoints for medication sync and status
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/medications", tags=["medications"])


@router.post("/sync")
async def webhook_sync_medications():
    """
    Webhook endpoint to trigger medication sync from Lambda
    
    Called by caregiver web app via ngrok to force immediate sync.
    This endpoint doesn't require payload - it just triggers a sync.
    """
    try:
        from services.medication_service import get_medication_service
        
        medication_service = get_medication_service()
        
        if not medication_service.is_running:
            return {
                "status": "not_running",
                "message": "Medication service is not running"
            }
        
        # Trigger immediate sync
        await medication_service._poll_medications()
        
        return {
            "status": "synced",
            "message": "Medications synced successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_medications():
    """
    Get all medications from local database
    
    Returns list of medications with their schedules and details
    """
    try:
        from services.medication_service import get_medication_service
        
        medication_service = get_medication_service()
        medications = medication_service.get_medications()
        
        return {
            "medications": medications,
            "count": len(medications)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{medication_id}")
async def get_medication(medication_id: str):
    """
    Get a specific medication by ID
    """
    try:
        from services.medication_service import get_medication_service
        
        medication_service = get_medication_service()
        medications = medication_service.get_medications()
        
        for med in medications:
            if med['medication_id'] == medication_id:
                return med
        
        raise HTTPException(status_code=404, detail="Medication not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/status")
async def get_medication_status():
    """
    Get medication service status
    
    Returns current status, active reminder, and statistics
    """
    try:
        from services.medication_service import get_medication_service
        
        medication_service = get_medication_service()
        medications = medication_service.get_medications()
        active_reminder = medication_service.active_reminder
        
        status = {
            "service_running": medication_service.is_running,
            "total_medications": len(medications),
            "active_reminder": active_reminder,
            "next_poll": None  # Could calculate from scheduler
        }
        
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

