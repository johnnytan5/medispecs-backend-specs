import os
from typing import Final
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Hardcoded User ID for MediSpecs Smart Glass
USER_ID: Final[str] = "u_123"

# Lambda API Configuration - loaded from .env
LAMBDA_API_URL: Final[str] = os.getenv("LAMBDA_API_URL")

# Database Configuration
DATABASE_URL: Final[str] = "sqlite+aiosqlite:///./reminders.db"

# Sync Configuration
AUTO_SYNC_ON_STARTUP: Final[bool] = True
CLEAR_ON_SYNC: Final[bool] = True  # Clear all local reminders before syncing

# Reminder Execution Configuration
ENABLE_REMINDER_EXECUTION: Final[bool] = False  # Set to True to enable scheduler
CHECK_INTERVAL_SECONDS: Final[int] = 60  # How often to check for due reminders

# OLED Display Configuration
OLED_ENABLED: Final[bool] = True  # Set to False to disable OLED display
OLED_FONT_SIZE: Final[int] = 14  # Default font size for OLED
OLED_BLINK_ON_REMINDER: Final[bool] = True  # Blink when showing reminders
OLED_DISPLAY_TIME: Final[int] = 10  # How long to show reminder (seconds)

