#!/usr/bin/env python3
"""
Quick test script to verify streaming functionality.
Run this after starting your FastAPI server to check if streaming works.
"""

import requests
import time
import sys


def test_server_health(base_url):
    """Test if server is running"""
    print("🔍 Testing server health...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running!")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to server: {e}")
        return False


def test_stream_status(base_url):
    """Test stream status endpoint"""
    print("\n🔍 Testing stream status endpoint...")
    try:
        response = requests.get(f"{base_url}/stream/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Stream status endpoint works!")
            print(f"   Status: {data.get('status')}")
            print(f"   Camera Running: {data.get('camera_running')}")
            print(f"   Camera Type: {data.get('camera_type')}")
            print(f"   Has Frame: {data.get('has_frame')}")
            
            if not data.get('camera_running'):
                print("\n⚠️  WARNING: Camera is not running!")
                print("   Make sure FACE_DETECTION_ENABLED=True in config.py")
                return False
            
            if not data.get('has_frame'):
                print("\n⚠️  WARNING: No frames captured yet")
                print("   Waiting for camera to capture first frame...")
                time.sleep(2)
            
            return True
        else:
            print(f"❌ Status endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to get status: {e}")
        return False


def test_stream_live(base_url):
    """Test if live stream endpoint returns data"""
    print("\n🔍 Testing live stream endpoint...")
    try:
        # Request first few bytes of stream
        response = requests.get(
            f"{base_url}/stream/live",
            stream=True,
            timeout=10
        )
        
        if response.status_code == 200:
            # Check content type
            content_type = response.headers.get('content-type', '')
            if 'multipart/x-mixed-replace' in content_type:
                print("✅ Stream endpoint is working!")
                print(f"   Content-Type: {content_type}")
                
                # Try to read first chunk
                print("   Reading first frame...")
                chunk_count = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        chunk_count += 1
                        if chunk_count >= 5:  # Read a few chunks
                            break
                
                print(f"   ✅ Successfully received {chunk_count} data chunks!")
                print(f"\n🎉 Stream is working! You can view it at:")
                print(f"   {base_url}/stream/live")
                return True
            else:
                print(f"❌ Wrong content type: {content_type}")
                return False
        else:
            print(f"❌ Stream endpoint returned {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print("❌ Timeout waiting for stream data")
        print("   Camera might not be capturing frames yet")
        return False
    except Exception as e:
        print(f"❌ Failed to access stream: {e}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("📹 MediSpecs Streaming Test Script")
    print("="*60)
    
    # Get base URL
    if len(sys.argv) > 1:
        base_url = sys.argv[1].rstrip('/')
    else:
        base_url = "http://localhost:8000"
    
    print(f"\n🌐 Testing server: {base_url}\n")
    
    # Run tests
    if not test_server_health(base_url):
        print("\n❌ Server is not accessible. Make sure it's running:")
        print("   python main.py")
        return 1
    
    if not test_stream_status(base_url):
        print("\n❌ Stream status check failed")
        return 1
    
    if not test_stream_live(base_url):
        print("\n❌ Live stream test failed")
        return 1
    
    print("\n" + "="*60)
    print("✅ All tests passed! Your streaming setup is working!")
    print("="*60)
    print("\n📖 Next steps:")
    print("   1. Open stream_viewer.html in your browser")
    print("   2. Enter the server URL")
    print("   3. Click 'Start Stream'")
    print("\n   Or view directly in browser:")
    print(f"   {base_url}/stream/live")
    print("\n   For remote access, use ngrok:")
    print("   ngrok http 8000")
    print("="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

