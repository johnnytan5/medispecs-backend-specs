from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import init_db, AsyncSessionLocal
from routers import reminders, webhooks, display, face_recognition, streaming, tts, stt
from services.reminder_service import ReminderService
from services.reminder_scheduler import get_scheduler
from services.face_detection_service import get_face_detection_service
from config import (
    USER_ID, 
    AUTO_SYNC_ON_STARTUP, 
    CLEAR_ON_SYNC, 
    ENABLE_REMINDER_EXECUTION,
    FACE_DETECTION_ENABLED,
    TTS_ENABLED,
    STT_ENABLED,
    STT_MODEL_PATH,
    STT_DEVICE_INDEX,
    LLM_ENABLED,
    LLM_API_KEY,
    LLM_MODEL,
    LLM_SYSTEM_PROMPT
)
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
    
    # Start face detection service (if enabled)
    face_detector = get_face_detection_service()
    await face_detector.start()
    
    if FACE_DETECTION_ENABLED:
        print(f"👤 Face detection enabled")
    else:
        print("⏸️  Face detection disabled (set FACE_DETECTION_ENABLED=True to enable)")
    
    # Initialize Text-to-Speech service (if enabled)
    if TTS_ENABLED:
        from services.tts_service import get_tts_service
        tts = get_tts_service()
        if tts.is_available:
            print(f"🔊 Text-to-Speech enabled")
        else:
            print(f"⚠️  Text-to-Speech initialization failed (voice output disabled)")
    else:
        print("⏸️  Text-to-Speech disabled (set TTS_ENABLED=True to enable)")
    
    # Initialize LLM service (if enabled)
    llm_service = None
    if LLM_ENABLED:
        from services.llm_service import get_llm_service
        llm_service = get_llm_service()
        
        if llm_service.initialize(LLM_API_KEY, LLM_MODEL, LLM_SYSTEM_PROMPT):
            print(f"🤖 LLM enabled - Voice commands will be processed by {LLM_MODEL}")
        else:
            print(f"⚠️  LLM initialization failed (voice commands won't be processed)")
            print(f"   Add OPENAI_API_KEY to .env file")
            llm_service = None
    else:
        print("⏸️  LLM disabled (set LLM_ENABLED=True to enable)")
    
    # Initialize Speech-to-Text service (if enabled)
    stt_service = None
    if STT_ENABLED:
        from services.stt_service import get_stt_service
        stt_service = get_stt_service()
        
        # Initialize with model
        if stt_service.initialize(STT_MODEL_PATH, STT_DEVICE_INDEX):
            print(f"🎤 Speech-to-Text initialized")
            
            # Start continuous listening for wake word
            await stt_service.start()
            print(f"👂 Listening for wake word: '{stt_service.wake_word}'")
        else:
            print(f"⚠️  Speech-to-Text initialization failed")
            print(f"   Download Vosk model from: https://alphacephei.com/vosk/models")
            print(f"   Place model in: {STT_MODEL_PATH}")
            stt_service = None
    else:
        print("⏸️  Speech-to-Text disabled (set STT_ENABLED=True to enable)")
    
    print(f"🎯 Service ready for user: {USER_ID}")
    print("=" * 60)
    
    yield
    
    # Shutdown: cleanup
    print("\n🛑 Shutting down MediSpecs API...")
    await scheduler.stop()
    await face_detector.stop()
    
    # Stop STT service if running
    if stt_service and stt_service.is_running:
        await stt_service.stop()
    
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
app.include_router(face_recognition.router)
app.include_router(streaming.router)
app.include_router(tts.router)
app.include_router(stt.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to MediSpecs API - Smart Glass Assistant for Senior Citizens",
        "status": "running",
        "version": "1.0.0",
        "features": [
            "Reminder Management",
            "Lambda API Sync",
            "Face Recognition (AWS Rekognition)",
            "Face Detection (YOLO v8)",
            "OLED Display Control",
            "Live Video Streaming (MJPEG)",
            "Text-to-Speech (Voice Reminders & Greetings)",
            "Speech-to-Text (Voice Commands with Wake Word)",
            "AI Voice Assistant (OpenAI GPT-3.5-Turbo)"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

