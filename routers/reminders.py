from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from database import get_db
from schemas import ReminderResponse
from services.reminder_service import ReminderService
from config import USER_ID

router = APIRouter(prefix="/reminders", tags=["reminders"])
reminder_service = ReminderService()


@router.get("/", response_model=List[ReminderResponse])
async def get_reminders(
    user_id: Optional[str] = Query(None, description="User ID (defaults to u_123)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all reminders from local database for a user.
    Defaults to hardcoded user_id (u_123).
    """
    user_id = user_id or USER_ID
    reminders = await reminder_service.get_local_reminders(db, user_id)
    return [ReminderResponse.from_orm(reminder) for reminder in reminders]


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(
    reminder_id: str,
    user_id: Optional[str] = Query(None, description="User ID (defaults to u_123)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific reminder from local database.
    Defaults to hardcoded user_id (u_123).
    """
    user_id = user_id or USER_ID
    reminder = await reminder_service.get_local_reminder(db, user_id, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return ReminderResponse.from_orm(reminder)


@router.get("/fetch/from-lambda", response_model=List[dict])
async def fetch_from_lambda(
    user_id: Optional[str] = Query(None, description="User ID (defaults to u_123)")
):
    """
    Fetch reminders directly from Lambda API without storing locally.
    Defaults to hardcoded user_id (u_123).
    Useful for testing/debugging.
    """
    user_id = user_id or USER_ID
    reminders = await reminder_service.fetch_reminders_from_lambda(user_id)
    return reminders
