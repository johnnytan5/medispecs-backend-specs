#!/usr/bin/env python3
"""
Simple test script to verify the MediSpecs API setup
Run this after starting the server with: uvicorn main:app --reload
"""

import asyncio
import httpx


BASE_URL = "http://localhost:8000"
USER_ID = "u_123"


async def test_health():
    """Test health endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"✓ Health Check: {response.json()}")


async def test_root():
    """Test root endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/")
        data = response.json()
        print(f"✓ Root: {data['message']}")
        print(f"  Features: {', '.join(data['features'])}")


async def test_get_reminders():
    """Test getting all reminders"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/reminders/")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Get Reminders: Found {len(data)} reminder(s)")
            for reminder in data[:5]:
                print(f"  - {reminder['title']} at {reminder.get('timeOfDay', 'N/A')}")
            return data[0]['reminderId'] if data else None
        else:
            print(f"✗ Get Reminders failed: {response.status_code}")
            return None


async def test_get_specific_reminder(reminder_id: str):
    """Test getting a specific reminder"""
    if not reminder_id:
        print("⊘ Get Specific Reminder skipped (no reminder ID)")
        return
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/reminders/{reminder_id}")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Get Specific Reminder: '{data['title']}' (version {data['version']})")
        else:
            print(f"✗ Get Specific Reminder failed: {response.status_code}")


async def test_fetch_from_lambda():
    """Test fetching reminders directly from Lambda"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/reminders/fetch/from-lambda")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Fetch from Lambda: Found {len(data)} reminder(s)")
            else:
                print(f"⚠ Fetch from Lambda: Status {response.status_code} (Lambda API may be unavailable)")
        except Exception as e:
            print(f"⚠ Fetch from Lambda: {e} (Lambda API may be unavailable)")


async def test_webhook_reminder_sync():
    """Test webhook to trigger reminder sync"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BASE_URL}/webhook/reminder")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Webhook Sync: {data['message']}")
                print(f"  Synced: {data['syncedCount']} reminders")
            else:
                print(f"⚠ Webhook Sync: Status {response.status_code}")
        except Exception as e:
            print(f"⚠ Webhook Sync: {e}")


async def test_display_status():
    """Test OLED display status"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/display/status")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Display Status: {data['status']}")
            else:
                print(f"⚠ Display Status: Status {response.status_code}")
        except Exception as e:
            print(f"⚠ Display Status: {e}")


async def test_display_message():
    """Test displaying a message on OLED"""
    async with httpx.AsyncClient() as client:
        try:
            test_message = "8PM TAKE MEDICINE"
            response = await client.post(
                f"{BASE_URL}/display/show",
                json={
                    "message": test_message,
                    "font_size": 14,
                    "should_blink": True,
                    "display_time": 3
                }
            )
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Display Message: {data['message']}")
            else:
                print(f"⚠ Display Message: Status {response.status_code}")
        except Exception as e:
            print(f"⚠ Display Message: {e}")


async def test_print_time_now():
    """Test displaying current time on OLED"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BASE_URL}/display/printtimenow")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Print Time Now: {data['time']} on {data['date']}")
            else:
                print(f"⚠ Print Time Now: Status {response.status_code}")
        except Exception as e:
            print(f"⚠ Print Time Now: {e}")


async def main():
    print("\n" + "="*60)
    print("MediSpecs API Test Suite - GET Endpoints Only")
    print("="*60 + "\n")
    
    try:
        # Basic tests
        await test_health()
        await test_root()
        print()
        
        # Reminder GET tests
        reminder_id = await test_get_reminders()
        await test_get_specific_reminder(reminder_id)
        await test_fetch_from_lambda()
        print()
        
        # Webhook test
        await test_webhook_reminder_sync()
        print()
        
        # Display tests
        await test_display_status()
        await test_display_message()
        await test_print_time_now()
        
        print("\n" + "="*60)
        print("✓ All tests completed!")
        print("="*60 + "\n")
        
    except httpx.ConnectError:
        print("\n✗ Error: Could not connect to API")
        print("Make sure the server is running: uvicorn main:app --reload")
    except Exception as e:
        print(f"\n✗ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
