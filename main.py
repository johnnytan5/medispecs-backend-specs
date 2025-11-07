from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import init_db, AsyncSessionLocal
from routers import reminders, webhooks, display
from services.reminder_service import ReminderService
from services.reminder_scheduler import get_scheduler
from config import USER_ID, AUTO_SYNC_ON_STARTUP, CLEAR_ON_SYNC, ENABLE_REMINDER_EXECUTION
import asyncio


async def init_reminders():
    """Initialize reminders by syncing from Lambda API"""
    if not AUTO_SYNC_ON_STARTUP:
        print("Auto-sync on startup is disabled")
        return
    
    print(f"🔄 Starting initial sync for user: {USER_ID}")
    reminder_service = ReminderService()
    
    try:
        async with AsyncSessionLocal() as db:
            synced_count = await reminder_service.sync_reminders_to_local(
                db, USER_ID, clear_first=CLEAR_ON_SYNC
            )
            print(f"✅ Successfully synced {synced_count} reminders from Lambda API")
    except Exception as e:
        print(f"⚠️  Error syncing reminders on startup: {e}")
        print("   The service will continue running, but no reminders were synced.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup: Initialize database
    print("🚀 Starting MediSpecs API...")
    await init_db()
    print("✅ Database initialized successfully")
    
    # Initialize reminders from Lambda API
    await init_reminders()
    
    # Start reminder scheduler (if enabled)
    scheduler = get_scheduler()
    await scheduler.start()
    
    if ENABLE_REMINDER_EXECUTION:
        from config import CHECK_INTERVAL_SECONDS
        print(f"⏰ Reminder execution enabled - checking every {CHECK_INTERVAL_SECONDS} seconds")
    else:
        print("⏸️  Reminder execution disabled (set ENABLE_REMINDER_EXECUTION=True to enable)")
    
    print(f"🎯 Service ready for user: {USER_ID}")
    print("=" * 60)
    
    yield
    
    # Shutdown: cleanup
    print("\n🛑 Shutting down MediSpecs API...")
    await scheduler.stop()
    print("=" * 60)


app = FastAPI(
    title="MediSpecs API",
    description="Backend API for MediSpecs Smart Glass - Senior Citizen Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(reminders.router)
app.include_router(webhooks.router)
app.include_router(display.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to MediSpecs API - Smart Glass Assistant for Senior Citizens",
        "status": "running",
        "version": "1.0.0",
        "features": ["Reminder Management", "Lambda API Sync"]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

