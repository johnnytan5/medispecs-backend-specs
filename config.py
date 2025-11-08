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

# Future: OpenAI LLM integration for processing voice commands
STT_OPENAI_ENABLED: Final[bool] = False  # Enable OpenAI LLM for command processing
STT_OPENAI_API_KEY: Final[str] = os.getenv("OPENAI_API_KEY", "")  # OpenAI API key
STT_OPENAI_MODEL: Final[str] = "gpt-4"  # Model to use for command processing

