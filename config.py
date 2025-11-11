import os
from typing import Final, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Hardcoded User ID for MediSpecs Smart Glass
USER_ID: Final[str] = "u_123"

# Lambda API Configuration - loaded from .env
# Single base URL for all Lambda functions (reminders, face recognition, etc.)
LAMBDA_API_URL: Final[str] = os.getenv("LAMBDA_API_URL")

# Sync Configuration
AUTO_SYNC_ON_STARTUP: Final[bool] = True
CLEAR_ON_SYNC: Final[bool] = True  # Clear all local reminders before syncing

# Reminder Execution Configuration
ENABLE_REMINDER_EXECUTION: Final[bool] = True  # Set to True to enable scheduler
CHECK_INTERVAL_SECONDS: Final[int] = 60  # How often to check for due reminders (every 1 minute)
DEBUG_SCHEDULER: Final[bool] = True  # Set to True to see verbose scheduler logs

# OLED Display Configuration
OLED_ENABLED: Final[bool] = True  # Set to False to disable OLED display
OLED_FONT_SIZE: Final[int] = 14  # Default font size for OLED
OLED_BLINK_ON_REMINDER: Final[bool] = True  # Blink when showing reminders
OLED_DISPLAY_TIME: Final[int] = 10  # How long to show reminder (seconds)

# Face Detection Configuration
FACE_DETECTION_ENABLED: Final[bool] = True  # Set to True to enable face detection
FACE_DETECTION_FPS: Final[int] = 2  # Detection frequency (2Hz = every 0.5 seconds)
FACE_CONFIRMATION_COUNT: Final[int] = 4  # Consecutive detections needed (4 * 0.5s = 2 seconds)
FACE_COOLDOWN_SECONDS: Final[int] = 10  # Wait time before detecting same area again
YOLO_MODEL: Final[str] = "yolov8n.pt"  # YOLO model (nano for speed)
CAMERA_INDEX: Final[int] = 0  # Camera device index (0 for default USB/Pi camera)
YOLO_CONFIDENCE_THRESHOLD: Final[float] = 0.65  # Minimum confidence (0.0-1.0) to consider a detection valid
YOLO_MIN_DETECTION_AREA: Final[int] = 100000  # Minimum bounding box area (px²) for face recognition (filters out distant/small detections)

# Text-to-Speech Configuration
TTS_ENABLED: Final[bool] = True  # Set to True to enable voice output
TTS_RATE: Final[int] = 130  # Speech rate in words per minute (100-130 recommended for seniors, slower than normal 150-200)
TTS_VOLUME: Final[float] = 0.9  # Volume level (0.0-1.0)
TTS_PREFER_FEMALE_VOICE: Final[bool] = True  # Use female voice if available

# TTS for different events
TTS_SPEAK_REMINDERS: Final[bool] = True  # Speak reminder text
TTS_SPEAK_FACE_GREETINGS: Final[bool] = True  # Speak greeting when face is recognized

# Future: ElevenLabs integration (set to enable custom voices)
TTS_ELEVENLABS_ENABLED: Final[bool] = False  # ElevenLabs custom voices (requires API key)
TTS_ELEVENLABS_API_KEY: Final[str] = os.getenv("ELEVENLABS_API_KEY", "")  # ElevenLabs API key
TTS_ELEVENLABS_VOICE_ID: Final[str] = os.getenv("ELEVENLABS_VOICE_ID", "")  # Custom voice ID

# Speech-to-Text Configuration (Vosk)
STT_ENABLED: Final[bool] = True  # Set to True to enable voice commands
STT_MODEL_PATH: Final[str] = os.getenv("STT_MODEL_PATH", "vosk-model-en-us-0.22")  # Path to Vosk model (renamed from 0.15)
STT_WAKE_WORD: Final[str] = "hey ruby"  # Wake word to activate voice commands
STT_COMMAND_TIMEOUT: Final[int] = 5  # Seconds to record command after wake word
STT_SAMPLE_RATE: Final[int] = 16000  # Audio sample rate (16kHz standard for speech)
STT_DEVICE_INDEX: Optional[int] = None  # Audio device index (None = default, or specific USB mic index)

# LLM Configuration (OpenAI GPT for voice command processing)
LLM_ENABLED: Final[bool] = True  # Enable LLM for processing voice commands
LLM_API_KEY: Final[str] = os.getenv("OPENAI_API_KEY", "")  # OpenAI API key from .env
LLM_MODEL: Final[str] = "gpt-3.5-turbo"  # Model: gpt-3.5-turbo (fast, cheap) or gpt-4 (best quality)
LLM_SYSTEM_PROMPT: Final[str] = (
    "You are Ruby, a helpful voice assistant for senior citizens. "
    "Be friendly, clear, and concise, super concise, and avoid using hard jargons and vocabularies, use easy words. "
    "You can only provide information and clarification. You CANNOT execute actions, create reminders, or control devices."
)
LLM_FALLBACK_MESSAGE: Final[str] = "I am not connected to internet right now"

# Vision Assistant Configuration (OpenAI GPT-4o with vision)
VISION_ENABLED: Final[bool] = True  # Enable vision-based commands
VISION_WAKE_WORD: Final[str] = "watch ruby"  # Wake word for vision commands
VISION_MODEL: Final[str] = "gpt-4o"  # GPT-4o (multimodal, fast, recommended)
VISION_COMMAND_TIMEOUT: Final[int] = 5  # Seconds to record command after wake word
VISION_GREETING: Final[str] = "I'm looking, go ahead"  # TTS greeting after wake word
VISION_FALLBACK_MESSAGE: Final[str] = "I can't see right now, camera not ready"  # When camera unavailable
VISION_SYSTEM_PROMPT: Final[str] = (
    "You are Ruby, a vision assistant for senior citizens. "
    "Look at the image and answer their question directly. "
    "Be friendly, clear, and concise, super concise. Use easy words and avoid hard jargons. "
    "Focus on what they asked about."
)

# Timelapse Recording Configuration
TIMELAPSE_ENABLED: Final[bool] = True  # Enable automatic timelapse recording
TIMELAPSE_FRAME_INTERVAL: Final[int] = 2  # Capture 1 frame every 2 seconds
TIMELAPSE_SEGMENT_DURATION: Final[int] = 900  # 15 minutes per video segment (900 seconds)
TIMELAPSE_VIDEO_FPS: Final[int] = 30  # Playback speed (30 FPS = smooth timelapse)
TIMELAPSE_VIDEO_QUALITY: Final[int] = 80  # Video quality (0-100, higher = better quality)
TIMELAPSE_STORAGE_PATH: Final[str] = "timelapse"  # Local storage directory
TIMELAPSE_MAX_AGE_HOURS: Final[int] = 24  # Delete local videos older than 24 hours

# Timelapse Upload Configuration
TIMELAPSE_UPLOAD_ENABLED: Final[bool] = True  # Auto-upload to S3 via Lambda
TIMELAPSE_LAMBDA_URL: Final[str] = os.getenv("LAMBDA_API_URL", "")  # Lambda API Gateway URL from .env
TIMELAPSE_UPLOAD_IMMEDIATE: Final[bool] = True  # Upload immediately after video creation
TIMELAPSE_UPLOAD_RETRY_IMMEDIATE: Final[int] = 3  # Immediate retry attempts on failure
TIMELAPSE_UPLOAD_RETRY_INTERVAL: Final[int] = 3600  # Background retry every 1 hour (3600 seconds)
TIMELAPSE_UPLOAD_MAX_ATTEMPTS: Final[int] = 24  # Max retry attempts (24 hours of hourly retries)
TIMELAPSE_DEVICE_ID: Final[str] = os.getenv("DEVICE_ID", "medispecs_pi_001")  # Device identifier

# ============================================================================
# Accelerometer Fall Detection Configuration (MPU6050)
# ============================================================================
ACCELEROMETER_ENABLED: Final[bool] = True  # Enable fall detection
ACCELEROMETER_I2C_ADDRESS: Final[int] = 0x3c  # MPU6050 I2C address
ACCELEROMETER_SAMPLING_RATE: Final[int] = 50  # Sampling frequency in Hz (50Hz = 20ms interval)

# Fall Detection Algorithm Thresholds
FALL_FREE_FALL_THRESHOLD: Final[float] = 0.4  # Free fall detection: total acceleration < 0.4G
FALL_IMPACT_THRESHOLD: Final[float] = 2.3  # Impact detection: total acceleration > 2.3G (slightly easier than 2.5G)
FALL_INACTIVITY_DURATION: Final[float] = 5.0  # Inactivity duration in seconds after impact
FALL_COOLDOWN_PERIOD: Final[int] = 20  # Cooldown period in seconds between fall detections

# Fall Response Configuration
FALL_CONFIRMATION_TIMEOUT: Final[int] = 30  # Seconds to wait for user's "okay" voice confirmation
FALL_CONFIRMATION_KEYWORD: Final[str] = "okay"  # Keyword to search in user's response (case-insensitive)
FALL_TTS_ALERT: Final[str] = "Fall detected! Are you okay? Please say okay"  # TTS message on fall
FALL_OLED_MESSAGE: Final[str] = "Fall Alert\nSpeak Up!"  # OLED message on fall
FALL_VIDEO_PREFIX: Final[str] = "FALL_"  # Prefix for fall-triggered timelapse segments

