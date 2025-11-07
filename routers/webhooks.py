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
    synced_count = await reminder_service.sync_reminders_to_local(
        db, USER_ID, clear_first=True
    )
    
    return {
        "status": "success",
        "message": f"Reminders refreshed from Lambda API",
        "userId": USER_ID,
        "syncedCount": synced_count,
        "action": "cleared_and_refreshed"
    }

