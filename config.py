import os
from typing import Final
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

