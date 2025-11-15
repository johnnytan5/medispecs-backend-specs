from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import init_db, AsyncSessionLocal
from routers import reminders, webhooks, display, face_recognition, streaming, tts, stt, timelapse, accelerometer, medications, location
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
    LLM_SYSTEM_PROMPT,
    VISION_ENABLED,
    VISION_MODEL,
    VISION_WAKE_WORD,
    TIMELAPSE_ENABLED,
    ACCELEROMETER_ENABLED,
    MEDICATION_ENABLED,
    LOCATION_ENABLED,
    BUTTON_ENABLED
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
            print(f"   Note: Vision mode removed (button-triggered STT is text-only)")
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
        import config
        
        stt_service = get_stt_service()
        
        # Initialize with model
        if stt_service.initialize(STT_MODEL_PATH, STT_DEVICE_INDEX, config.STT_COMMAND_TIMEOUT):
            print(f"🎤 Speech-to-Text initialized")
            print(f"   Mode: Button-triggered (no continuous wake word listening)")
            print(f"   Command timeout: {config.STT_COMMAND_TIMEOUT}s")
            
            # Start STT service (ready but not continuously listening)
            await stt_service.start()
        else:
            print(f"⚠️  Speech-to-Text initialization failed")
            print(f"   Download Vosk model from: https://alphacephei.com/vosk/models")
            print(f"   Place model in: {STT_MODEL_PATH}")
            stt_service = None
    else:
        print("⏸️  Speech-to-Text disabled (set STT_ENABLED=True to enable)")
    
    # Initialize Button service (for STT trigger) (if enabled)
    button_service = None
    if STT_ENABLED and config.BUTTON_ENABLED and stt_service:
        from services.button_service import get_button_service
        
        button_service = get_button_service()
        
        # Initialize button
        if button_service.initialize(
            button_pin=config.BUTTON_GPIO_PIN,
            pull_up=config.BUTTON_PULL_UP,
            bounce_time=config.BUTTON_BOUNCE_TIME
        ):
            # Set callback to trigger STT listening
            async def on_button_press():
                """Callback when button is pressed - trigger STT listening"""
                if stt_service and stt_service.is_running:
                    await stt_service.listen_on_button_press()
            
            button_service.set_callback(on_button_press)
            
            # Start button monitoring
            await button_service.start()
            print(f"🔘 Button service enabled (GPIO {config.BUTTON_GPIO_PIN})")
            print(f"   Press button to start voice listening")
        else:
            print(f"⚠️  Button service initialization failed")
            button_service = None
    else:
        if not STT_ENABLED:
            print("⏸️  Button service disabled (STT not enabled)")
        elif not config.BUTTON_ENABLED:
            print("⏸️  Button service disabled (set BUTTON_ENABLED=True to enable)")
    
    # Initialize Timelapse service (if enabled)
    timelapse_service = None
    if TIMELAPSE_ENABLED:
        from services.timelapse_service import get_timelapse_service
        import config
        
        timelapse_service = get_timelapse_service()
        
        # Prepare config dict
        timelapse_config = {
            'TIMELAPSE_FRAME_INTERVAL': config.TIMELAPSE_FRAME_INTERVAL,
            'TIMELAPSE_SEGMENT_DURATION': config.TIMELAPSE_SEGMENT_DURATION,
            'TIMELAPSE_VIDEO_FPS': config.TIMELAPSE_VIDEO_FPS,
            'TIMELAPSE_VIDEO_QUALITY': config.TIMELAPSE_VIDEO_QUALITY,
            'TIMELAPSE_STORAGE_PATH': config.TIMELAPSE_STORAGE_PATH,
            'TIMELAPSE_MAX_AGE_HOURS': config.TIMELAPSE_MAX_AGE_HOURS
        }
        
        if timelapse_service.initialize(timelapse_config):
            # Start recording automatically
            await timelapse_service.start()
            print(f"🎬 Timelapse recording enabled (1 frame/{config.TIMELAPSE_FRAME_INTERVAL}s, "
                  f"{config.TIMELAPSE_SEGMENT_DURATION//60}min segments)")
        else:
            print(f"⚠️  Timelapse initialization failed")
            timelapse_service = None
    else:
        print("⏸️  Timelapse disabled (set TIMELAPSE_ENABLED=True to enable)")
    
    # Initialize Accelerometer (Fall Detection) service (if enabled)
    accelerometer_service = None
    if ACCELEROMETER_ENABLED:
        from services.accelerometer_service import get_accelerometer_service
        import config
        
        accelerometer_service = get_accelerometer_service()
        
        # Prepare config dict
        accel_config = {
            'ACCELEROMETER_I2C_ADDRESS': config.ACCELEROMETER_I2C_ADDRESS,
            'ACCELEROMETER_SAMPLING_RATE': config.ACCELEROMETER_SAMPLING_RATE,
            'FALL_FREE_FALL_THRESHOLD': config.FALL_FREE_FALL_THRESHOLD,
            'FALL_IMPACT_THRESHOLD': config.FALL_IMPACT_THRESHOLD,
            'FALL_INACTIVITY_DURATION': config.FALL_INACTIVITY_DURATION,
            'FALL_COOLDOWN_PERIOD': config.FALL_COOLDOWN_PERIOD
        }
        
        if accelerometer_service.initialize(accel_config):
            # Register fall detection callback
            async def on_fall_detected(fall_event):
                """
                Callback when fall is detected
                1. Cut off timelapse video segment
                2. Play TTS alert
                3. Show OLED message
                4. Listen for "okay" confirmation
                5. Acknowledge fall based on response
                """
                try:
                    print(f"\n{'='*60}")
                    print(f"🚨 FALL DETECTED!")
                    print(f"{'='*60}")
                    
                    # 1. Cut off timelapse video (if recording)
                    if timelapse_service and timelapse_service.is_running:
                        video_id = await timelapse_service.trigger_fall_cutoff()
                        if video_id:
                            print(f"📹 Fall video segment saved: {video_id}")
                    
                    # 2. Play TTS alert + 3. Show OLED message (simultaneously)
                    from services.tts_service import get_tts_service
                    from services.oled_display import get_oled_service
                    
                    tts = get_tts_service()
                    oled = get_oled_service()
                    
                    # Fire and forget for TTS and OLED (simultaneous)
                    # OLED is synchronous, so run in thread pool
                    tts_task = asyncio.create_task(tts.speak_async(config.FALL_TTS_ALERT))
                    oled_task = asyncio.create_task(asyncio.to_thread(oled.show_message, config.FALL_OLED_MESSAGE))
                    
                    # Wait for both to complete (TTS might take longer)
                    await asyncio.gather(tts_task, oled_task)
                    
                    # 4. Listen for "okay" confirmation (if STT is available)
                    user_confirmed = False
                    response_text = None
                    
                    if stt_service and stt_service.is_running:
                        print(f"👂 Waiting for user confirmation...")
                        user_confirmed, response_text = await stt_service.listen_for_fall_confirmation(
                            timeout=config.FALL_CONFIRMATION_TIMEOUT,
                            keyword=config.FALL_CONFIRMATION_KEYWORD
                        )
                        
                        if user_confirmed:
                            print(f"✅ User confirmed: '{response_text}'")
                            # Speak positive response
                            await tts.speak_async("Glad you're okay!")
                        else:
                            print(f"⚠️  No confirmation received (timeout)")
                            # Emergency alert will be visible in /accelerometer/emergency/status endpoint
                    else:
                        print(f"⚠️  STT not available, cannot listen for confirmation")
                    
                    # 5. Acknowledge fall in accelerometer service
                    accelerometer_service.acknowledge_fall(user_confirmed, response_text)
                    
                    print(f"{'='*60}\n")
                
                except Exception as e:
                    print(f"\n❌ ERROR in fall detection callback: {e}")
                    import traceback
                    traceback.print_exc()
                    print(f"{'='*60}\n")
                    
                    # Still acknowledge the fall even if callback fails
                    try:
                        accelerometer_service.acknowledge_fall(False, None)
                    except:
                        pass
            
            # Set the callback
            accelerometer_service.on_fall_detected = on_fall_detected
            
            # Start monitoring
            await accelerometer_service.start()
            print(f"🚨 Fall detection enabled (sampling: {config.ACCELEROMETER_SAMPLING_RATE}Hz)")
            print(f"   Free fall: <{config.FALL_FREE_FALL_THRESHOLD}G, Impact: >{config.FALL_IMPACT_THRESHOLD}G")
        else:
            print(f"⚠️  Accelerometer initialization failed")
            accelerometer_service = None
    else:
        print("⏸️  Fall detection disabled (set ACCELEROMETER_ENABLED=True to enable)")
    
    # Initialize Medication service (if enabled)
    medication_service = None
    if MEDICATION_ENABLED:
        from services.medication_service import get_medication_service
        import config
        
        medication_service = get_medication_service()
        
        # Prepare config dict
        medication_config = {
            'MEDICATION_DB_PATH': config.MEDICATION_DB_PATH,
            'MEDICATION_LAMBDA_URL': config.MEDICATION_LAMBDA_URL,
            'MEDICATION_POLL_INTERVAL': config.MEDICATION_POLL_INTERVAL,
            'MEDICATION_CHECK_INTERVAL': config.MEDICATION_CHECK_INTERVAL,
            'MEDICATION_DETECTION_WINDOW': config.MEDICATION_DETECTION_WINDOW
        }
        
        if medication_service.initialize(medication_config):
            # Start medication service
            await medication_service.start()
            print(f"💊 Medication service enabled")
            print(f"   Polling Lambda every {config.MEDICATION_POLL_INTERVAL//3600}h")
            print(f"   Reminder window: {config.MEDICATION_DETECTION_WINDOW} minutes")
        else:
            print(f"⚠️  Medication service initialization failed")
            medication_service = None
    else:
        print("⏸️  Medication service disabled (set MEDICATION_ENABLED=True to enable)")
    
    # Initialize Location service (if enabled)
    location_service = None
    if LOCATION_ENABLED:
        from services.location_service import get_location_service
        import config
        
        location_service = get_location_service()
        
        # Prepare config dict
        location_config = {
            'LOCATION_DEVICE_ID': config.LOCATION_DEVICE_ID,
            'LOCATION_LAMBDA_URL': config.LOCATION_LAMBDA_URL,
            'LOCATION_UPDATE_INTERVAL': config.LOCATION_UPDATE_INTERVAL,
            'LOCATION_BATCH_INTERVAL': config.LOCATION_BATCH_INTERVAL,
            'LOCATION_GPS_PORT': config.LOCATION_GPS_PORT,
            'LOCATION_GPS_BAUDRATE': config.LOCATION_GPS_BAUDRATE
        }
        
        if location_service.initialize(location_config):
            # Auto-start location tracking
            await location_service.start()
            print(f"📍 Location tracking enabled")
            print(f"   Device ID: {config.LOCATION_DEVICE_ID}")
            print(f"   GPS Port: {config.LOCATION_GPS_PORT}")
            print(f"   Update interval: {config.LOCATION_UPDATE_INTERVAL}s")
            print(f"   Batch interval: {config.LOCATION_BATCH_INTERVAL}s")
        else:
            print(f"⚠️  Location service initialization failed")
            location_service = None
    else:
        print("⏸️  Location tracking disabled (set LOCATION_ENABLED=True to enable)")
    
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
    
    # Stop Timelapse service if running
    if timelapse_service and timelapse_service.is_running:
        await timelapse_service.stop()
    
    # Stop Accelerometer service if running
    if accelerometer_service and accelerometer_service.is_running:
        await accelerometer_service.stop()
    
    # Stop Medication service if running
    if medication_service and medication_service.is_running:
        await medication_service.stop()
    
    # Stop Location service if running
    if location_service and location_service.is_running:
        await location_service.stop()
    
    # Stop Button service if running
    if button_service and button_service.is_running:
        await button_service.stop()
    
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
app.include_router(timelapse.router)
app.include_router(accelerometer.router)
app.include_router(medications.router)
app.include_router(location.router)


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
            "AI Voice Assistant (OpenAI GPT-3.5-Turbo)",
            "AI Vision Assistant (OpenAI GPT-4o with Camera)",
            "Timelapse Recording (15-min segments, Auto-upload to S3)",
            "Fall Detection (MPU6050 Accelerometer with Voice Confirmation)",
            "Medication Reminders (TTS + OLED)",
            "Location Tracking (Neo-6M GPS with Lambda Upload)"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

