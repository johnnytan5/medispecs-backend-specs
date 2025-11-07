from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import re


class ReminderBase(BaseModel):
    title: str
    schedule_type: str = Field(..., alias="scheduleType")
    time_of_day: Optional[str] = Field(None, alias="timeOfDay")
    days_of_week: Optional[List[int]] = Field(default_factory=list, alias="daysOfWeek")
    device_id: Optional[str] = Field(None, alias="deviceId")

    @validator("time_of_day")
    def validate_time_format(cls, v):
        if v and not re.fullmatch(r"[0-2]\d:[0-5]\d", v):
            raise ValueError("timeOfDay must be in HH:MM format (24-hour)")
        return v

    @validator("schedule_type")
    def validate_schedule_type(cls, v):
        if v not in ["daily", "weekly"]:
            raise ValueError("scheduleType must be 'daily' or 'weekly'")
        return v

    @validator("days_of_week")
    def validate_days_of_week(cls, v, values):
        if values.get("schedule_type") == "weekly" and not v:
            raise ValueError("daysOfWeek is required for weekly schedule")
        if v:
            for day in v:
                if not 0 <= day <= 6:
                    raise ValueError("daysOfWeek must contain integers between 0 and 6")
        return v

    class Config:
        populate_by_name = True


class ReminderCreate(ReminderBase):
    user_id: Optional[str] = Field(None, alias="userId")


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    schedule_type: Optional[str] = Field(None, alias="scheduleType")
    time_of_day: Optional[str] = Field(None, alias="timeOfDay")
    days_of_week: Optional[List[int]] = Field(None, alias="daysOfWeek")
    device_id: Optional[str] = Field(None, alias="deviceId")

    @validator("time_of_day")
    def validate_time_format(cls, v):
        if v and not re.fullmatch(r"[0-2]\d:[0-5]\d", v):
            raise ValueError("timeOfDay must be in HH:MM format (24-hour)")
        return v

    class Config:
        populate_by_name = True


class ReminderResponse(ReminderBase):
    id: int
    reminder_id: str = Field(..., alias="reminderId")
    user_id: str = Field(..., alias="userId")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    version: int
    synced_at: Optional[datetime] = Field(None, alias="syncedAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class SyncResponse(BaseModel):
    synced_count: int = Field(..., alias="syncedCount")
    user_id: str = Field(..., alias="userId")
    message: str

