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


@router.post("/medications/sync")
async def webhook_medication_sync():
    """
    Webhook to trigger medication sync from Lambda API.
    Fetches latest medications and updates local SQLite database.
    Called by caregiver web app via ngrok.
    """
    print(f"\n{'='*60}")
    print(f"🔄 WEBHOOK: Syncing medications from Lambda API")
    print(f"   User: {USER_ID}")
    print(f"{'='*60}")
    
    try:
        from services.medication_service import get_medication_service
        
        medication_service = get_medication_service()
        
        if not medication_service.is_running:
            return {
                "status": "error",
                "message": "Medication service is not running"
            }
        
        # Trigger immediate sync
        await medication_service._poll_medications()
        
        medications = medication_service.get_medications()
        
        print(f"\n✅ Sync complete! Total medications: {len(medications)}")
        
        if medications:
            print(f"\nSynced medications:")
            for idx, med in enumerate(medications, 1):
                print(f"\n{idx}. [{med['medication_id']}]")
                print(f"   Name: {med['name']}")
                print(f"   Time: {med['time']}")
                print(f"   Frequency: {med['frequency']}")
        else:
            print("\n   ⚠️  No medications found after sync")
        
        print(f"\n{'='*60}\n")
        
        return {
            "status": "success",
            "message": "Medications refreshed from Lambda API",
            "userId": USER_ID,
            "syncedCount": len(medications),
            "action": "synced"
        }
    except Exception as e:
        print(f"\n❌ Error syncing medications: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n{'='*60}\n")
        return {
            "status": "error",
            "message": f"Failed to sync medications: {str(e)}"
        }

