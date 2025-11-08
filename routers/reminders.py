from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from database import get_db
from schemas import ReminderResponse
from services.reminder_service import ReminderService
from services.reminder_scheduler import get_scheduler
from config import USER_ID, ENABLE_REMINDER_EXECUTION, CHECK_INTERVAL_SECONDS

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


@router.get("/debug/status", response_model=dict)
async def debug_status(
    user_id: Optional[str] = Query(None, description="User ID (defaults to u_123)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Debug endpoint to check scheduler status, system time, and reminders.
    Helps diagnose why reminders might not be triggering on Raspberry Pi.
    """
    user_id = user_id or USER_ID
    
    # Get current system time
    now = datetime.now()
    current_time = now.time()
    current_day = now.weekday()
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Get scheduler status
    scheduler = get_scheduler()
    
    # Get all reminders from database
    reminders = await reminder_service.get_local_reminders(db, user_id)
    
    # Format reminders for display
    reminder_list = []
    for reminder in reminders:
        reminder_day = (current_day + 1) % 7  # Convert to reminder format (0=Sun)
        days_match = "N/A"
        if reminder.schedule_type == "weekly" and reminder.days_of_week:
            days_match = "YES" if reminder_day in reminder.days_of_week else "NO"
        elif reminder.schedule_type == "daily":
            days_match = "YES (daily)"
        
        reminder_list.append({
            "id": reminder.reminder_id,
            "title": reminder.title,
            "time": reminder.time_of_day,
            "schedule": reminder.schedule_type,
            "days_of_week": reminder.days_of_week,
            "current_day_matches": days_match
        })
    
    status = {
        "system_info": {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "current_time_only": current_time.strftime("%H:%M"),
            "current_day": day_names[current_day],
            "current_day_number": current_day,
            "current_day_reminder_format": (current_day + 1) % 7,
            "timezone": str(now.astimezone().tzinfo)
        },
        "scheduler_info": {
            "enabled": ENABLE_REMINDER_EXECUTION,
            "is_running": scheduler.is_running,
            "check_interval_seconds": CHECK_INTERVAL_SECONDS,
            "user_id": scheduler.user_id
        },
        "database_info": {
            "total_reminders": len(reminders),
            "reminders": reminder_list
        }
    }
    
    # Print detailed status to console
    print(f"\n{'='*60}")
    print(f"🔍 DEBUG STATUS CHECK")
    print(f"{'='*60}")
    print(f"⏰ SYSTEM TIME:")
    print(f"   Full: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Time: {current_time.strftime('%H:%M')}")
    print(f"   Day: {day_names[current_day]} (weekday: {current_day}, reminder format: {(current_day + 1) % 7})")
    print(f"   Timezone: {now.astimezone().tzinfo}")
    print(f"\n📊 SCHEDULER STATUS:")
    print(f"   Enabled: {ENABLE_REMINDER_EXECUTION}")
    print(f"   Running: {scheduler.is_running}")
    print(f"   Check Interval: {CHECK_INTERVAL_SECONDS} seconds")
    print(f"   User ID: {scheduler.user_id}")
    print(f"\n📋 DATABASE REMINDERS: {len(reminders)}")
    
    if reminders:
        for idx, reminder in enumerate(reminders, 1):
            print(f"\n   {idx}. [{reminder.reminder_id}]")
            print(f"      Title: {reminder.title}")
            print(f"      Time: {reminder.time_of_day or 'N/A'}")
            print(f"      Schedule: {reminder.schedule_type}")
            if reminder.days_of_week:
                days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                day_names_list = [days[d] for d in reminder.days_of_week]
                print(f"      Days: {', '.join(day_names_list)} {reminder.days_of_week}")
            
            # Check if this reminder should trigger now
            if reminder.time_of_day:
                try:
                    hour, minute = map(int, reminder.time_of_day.split(':'))
                    time_matches = (current_time.hour == hour and current_time.minute == minute)
                    
                    if reminder.schedule_type == "daily":
                        should_trigger = time_matches
                    elif reminder.schedule_type == "weekly":
                        reminder_day = (current_day + 1) % 7
                        should_trigger = time_matches and reminder_day in (reminder.days_of_week or [])
                    else:
                        should_trigger = False
                    
                    print(f"      Time Match: {time_matches}")
                    print(f"      Would Trigger NOW: {'🔔 YES' if should_trigger else '❌ NO'}")
                except:
                    pass
    else:
        print("   ⚠️  No reminders in database!")
    
    print(f"{'='*60}\n")
    
    return status
