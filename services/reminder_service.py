import httpx
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Reminder
import os


class ReminderService:
    def __init__(self):
        self.base_url = os.getenv(
            "LAMBDA_API_URL",
            "https://zqglpdheqk.execute-api.ap-southeast-1.amazonaws.com/staging"
        )
        self.timeout = httpx.Timeout(30.0)

    async def fetch_reminders_from_lambda(self, user_id: str) -> List[dict]:
        """Fetch all reminders for a user from Lambda API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/reminders",
                    params={"userId": user_id}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error fetching reminders from Lambda: {e}")
                return []

    async def fetch_reminder_from_lambda(self, user_id: str, reminder_id: str) -> Optional[dict]:
        """Fetch a specific reminder from Lambda API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/reminders/{reminder_id}",
                    params={"userId": user_id}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error fetching reminder from Lambda: {e}")
                return None

    async def create_reminder_in_lambda(self, user_id: str, reminder_data: dict) -> Optional[dict]:
        """Create a reminder in Lambda API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                payload = {**reminder_data, "userId": user_id}
                response = await client.post(
                    f"{self.base_url}/reminders",
                    json=payload,
                    params={"userId": user_id}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error creating reminder in Lambda: {e}")
                return None

    async def update_reminder_in_lambda(
        self, user_id: str, reminder_id: str, reminder_data: dict
    ) -> Optional[dict]:
        """Update a reminder in Lambda API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.patch(
                    f"{self.base_url}/reminders/{reminder_id}",
                    json=reminder_data,
                    params={"userId": user_id}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error updating reminder in Lambda: {e}")
                return None

    async def delete_reminder_in_lambda(self, user_id: str, reminder_id: str) -> bool:
        """Delete a reminder in Lambda API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.delete(
                    f"{self.base_url}/reminders/{reminder_id}",
                    params={"userId": user_id}
                )
                response.raise_for_status()
                return True
            except httpx.HTTPError as e:
                print(f"Error deleting reminder in Lambda: {e}")
                return False

    async def clear_all_local_reminders(self, db: AsyncSession, user_id: str) -> int:
        """Clear all local reminders for a user"""
        stmt = select(Reminder).where(Reminder.user_id == user_id)
        result = await db.execute(stmt)
        reminders = result.scalars().all()
        
        count = len(reminders)
        for reminder in reminders:
            await db.delete(reminder)
        
        await db.commit()
        return count

    async def sync_reminders_to_local(
        self, db: AsyncSession, user_id: str, clear_first: bool = False
    ) -> int:
        """
        Sync all reminders from Lambda to local SQLite database
        
        Args:
            db: Database session
            user_id: User identifier
            clear_first: If True, clear all existing reminders before syncing
        
        Returns:
            Number of reminders synced
        """
        # Clear existing reminders if requested
        if clear_first:
            cleared_count = await self.clear_all_local_reminders(db, user_id)
            print(f"Cleared {cleared_count} existing reminders for user {user_id}")
        
        lambda_reminders = await self.fetch_reminders_from_lambda(user_id)
        synced_count = 0

        for lambda_reminder in lambda_reminders:
            reminder_id = lambda_reminder.get("reminderId")
            if not reminder_id:
                continue

            # Check if reminder exists locally
            stmt = select(Reminder).where(
                Reminder.reminder_id == reminder_id,
                Reminder.user_id == user_id
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            reminder_data = {
                "reminder_id": reminder_id,
                "user_id": user_id,
                "title": lambda_reminder.get("title"),
                "schedule_type": lambda_reminder.get("scheduleType"),
                "time_of_day": lambda_reminder.get("timeOfDay"),
                "days_of_week": lambda_reminder.get("daysOfWeek", []),
                "device_id": lambda_reminder.get("deviceId"),
                "version": lambda_reminder.get("version", 1),
                "synced_at": datetime.utcnow(),
            }

            # Parse timestamps if present
            if lambda_reminder.get("createdAt"):
                try:
                    reminder_data["created_at"] = datetime.fromisoformat(
                        lambda_reminder["createdAt"].replace("Z", "+00:00")
                    )
                except:
                    pass

            if lambda_reminder.get("updatedAt"):
                try:
                    reminder_data["updated_at"] = datetime.fromisoformat(
                        lambda_reminder["updatedAt"].replace("Z", "+00:00")
                    )
                except:
                    pass

            if existing:
                # Update existing reminder
                for key, value in reminder_data.items():
                    setattr(existing, key, value)
            else:
                # Create new reminder
                new_reminder = Reminder(**reminder_data)
                db.add(new_reminder)

            synced_count += 1

        await db.commit()
        return synced_count

    async def get_local_reminders(self, db: AsyncSession, user_id: str) -> List[Reminder]:
        """Get all reminders from local database"""
        stmt = select(Reminder).where(Reminder.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_local_reminder(
        self, db: AsyncSession, user_id: str, reminder_id: str
    ) -> Optional[Reminder]:
        """Get a specific reminder from local database"""
        stmt = select(Reminder).where(
            Reminder.user_id == user_id,
            Reminder.reminder_id == reminder_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_local_reminder(
        self, db: AsyncSession, user_id: str, reminder_data: dict
    ) -> Reminder:
        """Create a reminder in local database"""
        # Generate reminder ID if not provided
        if "reminder_id" not in reminder_data:
            reminder_data["reminder_id"] = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")

        reminder_data["user_id"] = user_id
        new_reminder = Reminder(**reminder_data)
        db.add(new_reminder)
        await db.commit()
        await db.refresh(new_reminder)
        return new_reminder

    async def update_local_reminder(
        self, db: AsyncSession, user_id: str, reminder_id: str, reminder_data: dict
    ) -> Optional[Reminder]:
        """Update a reminder in local database"""
        reminder = await self.get_local_reminder(db, user_id, reminder_id)
        if not reminder:
            return None

        for key, value in reminder_data.items():
            if value is not None and hasattr(reminder, key):
                setattr(reminder, key, value)

        reminder.updated_at = datetime.utcnow()
        reminder.version += 1

        await db.commit()
        await db.refresh(reminder)
        return reminder

    async def delete_local_reminder(
        self, db: AsyncSession, user_id: str, reminder_id: str
    ) -> bool:
        """Delete a reminder from local database"""
        reminder = await self.get_local_reminder(db, user_id, reminder_id)
        if not reminder:
            return False

        await db.delete(reminder)
        await db.commit()
        return True

