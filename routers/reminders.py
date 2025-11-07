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
    
    # Print reminders to console
    print(f"\n{'='*60}")
    print(f"📋 GET REMINDERS for user: {user_id}")
    print(f"   Total reminders: {len(reminders)}")
    print(f"{'='*60}")
    
    if reminders:
        for idx, reminder in enumerate(reminders, 1):
            print(f"\n{idx}. [{reminder.reminder_id}]")
            print(f"   Title: {reminder.title}")
            print(f"   Schedule: {reminder.schedule_type}")
            print(f"   Time: {reminder.time_of_day or 'N/A'}")
            if reminder.days_of_week:
                days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                day_names = [days[d] for d in reminder.days_of_week]
                print(f"   Days: {', '.join(day_names)}")
            print(f"   Version: {reminder.version}")
    else:
        print("\n   ⚠️  No reminders found")
    
    print(f"\n{'='*60}\n")
    
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
    
    print(f"\n{'='*60}")
    print(f"📋 GET SINGLE REMINDER: {reminder_id}")
    print(f"   User: {user_id}")
    print(f"{'='*60}")
    
    if not reminder:
        print(f"   ❌ Reminder not found")
        print(f"{'='*60}\n")
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    print(f"   ✅ Found:")
    print(f"   Title: {reminder.title}")
    print(f"   Schedule: {reminder.schedule_type}")
    print(f"   Time: {reminder.time_of_day or 'N/A'}")
    if reminder.days_of_week:
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        day_names = [days[d] for d in reminder.days_of_week]
        print(f"   Days: {', '.join(day_names)}")
    print(f"{'='*60}\n")
    
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
    
    print(f"\n{'='*60}")
    print(f"🌐 FETCH FROM LAMBDA for user: {user_id}")
    print(f"   Total reminders: {len(reminders)}")
    print(f"{'='*60}")
    
    if reminders:
        for idx, reminder in enumerate(reminders, 1):
            print(f"\n{idx}. [{reminder.get('reminderId', 'N/A')}]")
            print(f"   Title: {reminder.get('title', 'N/A')}")
            print(f"   Schedule: {reminder.get('scheduleType', 'N/A')}")
            print(f"   Time: {reminder.get('timeOfDay', 'N/A')}")
            if reminder.get('daysOfWeek'):
                days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                day_names = [days[d] for d in reminder['daysOfWeek']]
                print(f"   Days: {', '.join(day_names)}")
    else:
        print("\n   ⚠️  No reminders found in Lambda")
    
    print(f"\n{'='*60}\n")
    
    return reminders
