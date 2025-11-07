from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime
from database import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    reminder_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    schedule_type = Column(String, nullable=False)  # 'daily' or 'weekly'
    time_of_day = Column(String, nullable=True)  # HH:MM format
    days_of_week = Column(JSON, nullable=True)  # List of integers [0-6] for weekly
    device_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(Integer, default=1)
    synced_at = Column(DateTime, nullable=True)  # Last sync with Lambda API

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "reminderId": self.reminder_id,
            "userId": self.user_id,
            "title": self.title,
            "scheduleType": self.schedule_type,
            "timeOfDay": self.time_of_day,
            "daysOfWeek": self.days_of_week or [],
            "deviceId": self.device_id,
            "createdAt": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() + "Z" if self.updated_at else None,
            "version": self.version,
            "syncedAt": self.synced_at.isoformat() + "Z" if self.synced_at else None,
        }

