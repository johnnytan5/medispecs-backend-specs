# 🚀 QUICKSTART: Docker on Raspberry Pi

## ✅ Prerequisites

1. **Raspberry Pi** (tested on Pi 3/4/5)
2. **Raspberry Pi Camera** connected and enabled
3. **Docker** and **Docker Compose** installed
4. **Camera enabled** in raspi-config

---

## 📋 Step-by-Step Setup

### 1️⃣ Enable Camera (if not already done)

```bash
sudo raspi-config
# Interface Options → Camera → Enable
# Reboot if prompted
```

Verify camera works:
```bash
libcamera-hello
# Should show camera preview for 5 seconds
```

---

### 2️⃣ Clone Repository

```bash
cd ~
git clone <your-repo-url> medispecs-backend-specs
cd medispecs-backend-specs
```

---

### 3️⃣ Create .env File

```bash
nano .env
```

Add this content:
```env
LAMBDA_API_URL=https://zqglpdheqk.execute-api.ap-southeast-1.amazonaws.com/staging
USER_ID=u_123
```

Save: `Ctrl+X`, `Y`, `Enter`

---

### 4️⃣ Run the Quick Start Script

```bash
chmod +x DOCKER_RUN.sh
./DOCKER_RUN.sh
```

This will:
- ✅ Check if .env exists (create if missing)
- ✅ Check camera and I2C access
- ✅ Build Docker image with picamera2
- ✅ Start the service

**Build time:** 5-10 minutes (first time only)

---

## 📊 Verify It's Working

### Check logs
```bash
docker-compose logs -f
```

You should see:
```
✅ Pi Camera opened successfully (picamera2)
🔍 Loading YOLO model: yolov8n.pt
✅ YOLO model loaded successfully
▶️  Face detection started
```

### Test the API
```bash
curl http://localhost:8000/
```

Should return JSON with service info.

### Check face detection status
```bash
curl http://localhost:8000/face/status
```

---

## 🎥 Camera Troubleshooting

### Issue: "Failed to import picamera2"

**Solution 1:** Rebuild with no cache
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

**Solution 2:** Check picamera2 in container
```bash
docker exec -it medispecs-api python -c "from picamera2 import Picamera2; print('OK')"
```

### Issue: "Failed to open camera"

**Check 1:** Camera is enabled
```bash
vcgencmd get_camera
# Should show: supported=1 detected=1
```

**Check 2:** Devices are mapped
```bash
ls -la /dev/video* /dev/vchiq
# All should exist
```

**Check 3:** Restart Docker
```bash
docker-compose restart
```

### Issue: Blue colors (Avatar effect)

✅ **Already fixed!** The code now properly handles RGB format from picamera2.

---

## 🛠️ Common Commands

### View logs (live)
```bash
docker-compose logs -f
```

### Stop service
```bash
docker-compose down
```

### Start service (after stopping)
```bash
docker-compose up -d
```

### Restart service
```bash
docker-compose restart
```

### Rebuild image
```bash
docker-compose build --no-cache
```

### Check running containers
```bash
docker ps
```

### Enter container shell
```bash
docker exec -it medispecs-api bash
```

---

## ⚙️ Configuration

Edit `config.py` to adjust:

```python
# Face Detection
FACE_DETECTION_ENABLED = True          # Enable/disable face detection
FACE_DETECTION_FPS = 2                 # Detection rate (2Hz)
FACE_CONFIRMATION_COUNT = 4            # Detections needed (4 * 0.5s = 2s)
FACE_COOLDOWN_SECONDS = 10             # Cooldown after recognition
YOLO_CONFIDENCE_THRESHOLD = 0.65       # Detection confidence (0.0-1.0)

# Camera
CAMERA_INDEX = 0                       # Camera device index

# OLED Display
OLED_ENABLED = True                    # Enable/disable OLED
OLED_BLINK_ON_REMINDER = True          # Blink on reminders
```

After changes, restart:
```bash
docker-compose restart
```

---

## 🔍 What's Installed

The Docker image includes:

✅ **Python 3.11** (Debian Bookworm base)  
✅ **picamera2** (direct pip install with all dependencies)  
✅ **YOLO v8** (ultralytics)  
✅ **OpenCV** (headless, for image processing)  
✅ **FastAPI** (API framework)  
✅ **SQLite** (local database)  
✅ **luma.oled** (OLED display support)  

---

## 📍 API Endpoints

Once running, access at `http://localhost:8000`

### Main Endpoints

- `GET /` - API info
- `GET /health` - Health check
- `GET /face/status` - Face detection status
- `GET /face/family` - List family members
- `POST /face/recognize` - Manual face recognition
- `GET /reminders` - Get all reminders
- `POST /webhook/reminder` - Sync reminders from Lambda

### Example: Test Face Detection Status

```bash
curl http://localhost:8000/face/status
```

Response:
```json
{
  "service": "face_detection",
  "enabled": true,
  "running": true,
  "using_picamera": true,
  "camera_initialized": true
}
```

---

## 🆘 Emergency Stop

If something goes wrong:

```bash
# Stop and remove everything
docker-compose down

# Remove volumes (will delete database)
docker volume rm medispecs-backend-specs_db_data

# Start fresh
./DOCKER_RUN.sh
```

---

## ✅ Success Indicators

You know it's working when:

1. ✅ Docker builds without errors
2. ✅ Logs show "Pi Camera opened successfully (picamera2)"
3. ✅ Logs show "Face detection started"
4. ✅ API responds at http://localhost:8000
5. ✅ `/face/status` shows `"using_picamera": true`

---

## 📞 Need Help?

Check these files for more details:

- `RUN_ON_RASPBERRY_PI.txt` - Comprehensive setup guide
- `ENV_SETUP.txt` - Environment variables
- `docker-compose.yml` - Docker configuration
- `Dockerfile` - Image build instructions

---

**Last Updated:** November 2025  
**Tested On:** Raspberry Pi 4B, Raspberry Pi OS Bookworm (64-bit)

