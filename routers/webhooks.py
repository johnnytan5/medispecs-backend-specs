from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.reminder_service import ReminderService
from config import USER_ID

router = APIRouter(prefix="/webhook", tags=["webhooks"])
reminder_service = ReminderService()


@router.post("/reminder")
async def webhook_reminder_sync(db: AsyncSession = Depends(get_db)):
    """
    Webhook to trigger reminder sync from Lambda API.
    Fetches latest reminders, clears local SQLite database, and refreshes with new data.
    """
    print(f"\n{'='*60}")
    print(f"🔄 WEBHOOK: Syncing reminders from Lambda API")
    print(f"   User: {USER_ID}")
    print(f"{'='*60}")
    
    synced_count = await reminder_service.sync_reminders_to_local(
        db, USER_ID, clear_first=True
    )
    
    # Fetch and display the synced reminders
    reminders = await reminder_service.get_local_reminders(db, USER_ID)
    
    print(f"\n✅ Sync complete! Total reminders: {synced_count}")
    
    if reminders:
        print(f"\nSynced reminders:")
        for idx, reminder in enumerate(reminders, 1):
            print(f"\n{idx}. [{reminder.reminder_id}]")
            print(f"   Title: {reminder.title}")
            print(f"   Schedule: {reminder.schedule_type}")
            print(f"   Time: {reminder.time_of_day or 'N/A'}")
            if reminder.days_of_week:
                days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                day_names = [days[d] for d in reminder.days_of_week]
                print(f"   Days: {', '.join(day_names)}")
    else:
        print("\n   ⚠️  No reminders found after sync")
    
    print(f"\n{'='*60}\n")
    
    return {
        "status": "success",
        "message": f"Reminders refreshed from Lambda API",
        "userId": USER_ID,
        "syncedCount": synced_count,
        "action": "cleared_and_refreshed"
    }

