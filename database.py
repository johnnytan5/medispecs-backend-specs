from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os
from pathlib import Path

# Determine data directory (Docker vs local)
# Check multiple indicators for Docker environment
is_docker = (
    os.path.exists("/.dockerenv") or  # Docker creates this file
    os.getenv("DOCKER_CONTAINER") == "true" or  # We set this in docker-compose
    Path("/app").exists() and os.access("/app", os.W_OK)  # /app exists and writable
)

if is_docker:
    # Running in Docker
    data_dir = Path("/app/data")
else:
    # Running locally - use current directory
    data_dir = Path(__file__).parent / "data"

# Ensure data directory exists
data_dir.mkdir(parents=True, exist_ok=True)

# SQLite database URL (use absolute path)
db_path = data_dir.absolute() / "reminders.db"
SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"

# Debug: Print database location
print(f"📁 Database location: {db_path}")
print(f"   Running in Docker: {is_docker}")

# Create async engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

