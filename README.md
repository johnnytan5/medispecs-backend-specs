# RemindAR - Smart Glass Backend

> **"Taking care of my grandfather is hard, because he'll often forget if he'd took his medicine or lunch, let alone remembering our faces"** - One of our team members

Alzheimer patients are hard, but the burden that caregivers face are a tougher challenge. Missed medications, missed food, aimless stroll forgetting their way back, the list goes on.

That's why our team - **Pacific KMPP** decided to come up with **RemindAR**, a solution that's both designed for enabling senior alzheimer citizens to live with dignity, and for caregivers to have peace of mind, offloading their caregiving burden.

## 🎯 Project Overview

RemindAR is a smart glass system designed to combat Alzheimer's disease by providing comprehensive support for senior citizens and their caregivers. The backend API powers a Raspberry Pi-based smart glass device that offers memory assistance, proactive crisis prevention, and efficient caregiving tools.

## ✨ Key Features

### Enhanced Memory and Cognitive Support for Seniors
- **Reminders**: Provides reminders set by caregivers for medications, meals, and daily activities
- **Cognitive Training**: Interactive cognitive exercises to maintain mental acuity
- **Family Member Face Recognition**: Recognizes and greets family members using AWS Rekognition

### Proactive Crisis Prevention
- **Geo-Fencing Alerts**: Monitors location and alerts caregivers when the user leaves a safe zone
- **Fall Detection**: Real-time accelerometer-based fall detection with voice confirmation
- **Instant Caregiver Alerts**: Immediate notifications to caregivers during emergencies

### Efficient Caregiving
- **Timelapse Recording Playback**: Automatic video recording with 15-minute segments, auto-uploaded to S3
- **Live GPS Tracking**: Real-time location tracking with batch updates to Lambda API
- **Live Camera Stream**: MJPEG video streaming for remote monitoring

## 🏗️ Core Functions

### 1. **Reminder Management**
- Syncs reminders from AWS Lambda API on startup
- Executes reminders at scheduled times with TTS and OLED display
- Supports medication reminders, meal reminders, and custom notifications

### 2. **Face Recognition**
- YOLO v8-based face detection
- AWS Rekognition integration for family member identification
- Automatic greetings when family members are recognized

### 3. **Voice Assistant (Ruby)**
- Speech-to-Text using Vosk (offline) with button-triggered activation
- Text-to-Speech using gTTS (online) with pyttsx3 fallback (offline)
- OpenAI GPT-4o integration for natural language processing
- Voice commands for information and clarification

### 4. **Fall Detection**
- MPU6050 accelerometer monitoring at 50Hz
- Free-fall and impact detection algorithms
- Voice confirmation system ("Are you okay?")
- Automatic timelapse video cutoff on fall detection
- Emergency status tracking for caregivers

### 5. **Medication Management**
- Automatic polling from Lambda API every 2 hours
- Medication reminder window detection (5 minutes after scheduled time)
- TTS and OLED reminders for medication intake
- Medication history tracking

### 6. **Location Tracking**
- Neo-6M GPS module integration
- Real-time location updates (1 second intervals)
- Batch upload to Lambda API (10 second intervals)
- Geo-fencing support for safe zone monitoring

### 7. **Timelapse Recording**
- Automatic frame capture (1 frame per 2 seconds)
- 15-minute video segments at 30 FPS
- Auto-upload to S3 via Lambda API
- Local storage cleanup (24-hour retention)

### 8. **Live Streaming**
- MJPEG video streaming endpoint
- Camera support (USB or Raspberry Pi Camera)
- Real-time video feed for remote monitoring

## 🚀 Getting Started

### Prerequisites

- **Hardware**:
  - Raspberry Pi (recommended: Pi 4 or newer)
  - OLED Display (I2C)
  - MPU6050 Accelerometer (I2C)
  - Neo-6M GPS Module (Serial/UART)
  - Camera (USB or Pi Camera)
  - Microphone (USB or built-in)
  - Button (GPIO)

- **Software**:
  - Python 3.11+
  - Docker & Docker Compose (optional)
  - ngrok (for exposing port 8000)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd medispecs-backend-specs
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download Vosk Speech Recognition Model**
   - The model is already included in `vosk-model-en-us-0.22/`
   - If needed, download from: https://alphacephei.com/vosk/models

4. **Download YOLO Model**
   - The model file `yolov8n.pt` should be in the project root
   - It will be auto-downloaded on first run if missing

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# AWS Lambda API Gateway URL (required)
LAMBDA_API_URL=https://your-api-gateway-url.execute-api.region.amazonaws.com/staging

# OpenAI API Key (required for LLM voice assistant)
OPENAI_API_KEY=sk-your-openai-api-key

# Device ID (optional, defaults to medispecs_pi_001)
DEVICE_ID=medispecs_pi_001

# Speech-to-Text Model Path (optional, defaults to vosk-model-en-us-0.22)
STT_MODEL_PATH=vosk-model-en-us-0.22

# ElevenLabs API (optional, for custom TTS voices)
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_VOICE_ID=your-voice-id
```

### AWS Credentials Setup

The backend communicates with AWS services through Lambda API Gateway. AWS credentials are handled by the Lambda functions, not directly by this backend.

**Required AWS Services:**
- **AWS Lambda**: API Gateway endpoints for reminders, face recognition, medication, location, and timelapse upload
- **AWS Rekognition**: Face recognition service (accessed via Lambda)
- **AWS S3**: Storage for timelapse videos and family member photos (accessed via Lambda)

**Configuration:**
1. Ensure your Lambda API Gateway URL is set in `LAMBDA_API_URL` environment variable
2. The Lambda functions should have proper IAM roles with permissions for:
   - Rekognition: `rekognition:DetectFaces`, `rekognition:SearchFacesByImage`
   - S3: `s3:PutObject`, `s3:GetObject`
   - DynamoDB (if used): Appropriate read/write permissions

**Note**: This backend does not require direct AWS credentials. All AWS operations are performed server-side through the Lambda API Gateway.

### Running the Application

#### Option 1: Direct Python Execution

```bash
# Make sure you're in the project directory
python main.py
```

The API will start on `http://0.0.0.0:8000`

#### Option 2: Using Docker Compose

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Exposing Port 8000 with ngrok

To expose the API for external access (e.g., for webhooks or remote monitoring):

1. **Install ngrok**
   ```bash
   # macOS
   brew install ngrok
   
   # Or download from https://ngrok.com/download
   ```

2. **Start ngrok tunnel**
   ```bash
   ngrok http 8000
   ```

3. **Copy the forwarding URL**
   - ngrok will display a URL like: `https://abc123.ngrok.io`
   - Use this URL for webhooks or external API access
   - The URL will be available at: `https://abc123.ngrok.io/`

4. **Update webhook URLs** (if needed)
   - Update any webhook configurations to use the ngrok URL
   - Note: Free ngrok URLs change on restart. Consider ngrok paid plan for static URLs

**Example ngrok output:**
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

## 📡 API Endpoints

### Health & Status
- `GET /` - API information and feature list
- `GET /health` - Health check endpoint

### Reminders
- `GET /reminders` - List all reminders
- `GET /reminders/{id}` - Get specific reminder
- `POST /reminders` - Create reminder
- `PUT /reminders/{id}` - Update reminder
- `DELETE /reminders/{id}` - Delete reminder
- `POST /reminders/sync` - Sync reminders from Lambda API

### Face Recognition
- `POST /face/recognize` - Recognize face from image
- `GET /face/family` - List registered family members
- `GET /face/status` - Face recognition service status

### Display
- `POST /display/message` - Show message on OLED display
- `POST /display/clear` - Clear OLED display

### Streaming
- `GET /stream` - MJPEG video stream

### Text-to-Speech
- `POST /tts/speak` - Speak text
- `GET /tts/status` - TTS service status

### Speech-to-Text
- `POST /stt/listen` - Listen for voice command
- `GET /stt/status` - STT service status

### Timelapse
- `GET /timelapse/videos` - List recorded videos
- `GET /timelapse/videos/{video_id}` - Get video details
- `GET /timelapse/videos/{video_id}/download` - Download video

### Accelerometer (Fall Detection)
- `GET /accelerometer/status` - Accelerometer status
- `GET /accelerometer/emergency/status` - Emergency fall status
- `POST /accelerometer/emergency/acknowledge` - Acknowledge fall

### Medications
- `GET /medications` - List medications
- `GET /medications/{medication_id}` - Get medication details
- `POST /medications/{medication_id}/taken` - Mark medication as taken

### Location
- `GET /location/current` - Get current GPS location
- `GET /location/history` - Get location history
- `POST /location/update` - Manually update location

### Webhooks
- `POST /webhooks/reminder` - Webhook endpoint for reminder updates

## 🔧 Configuration

Most configuration options are in `config.py`. Key settings include:

- **Reminder Execution**: Enable/disable reminder scheduler
- **Face Detection**: YOLO model settings and detection thresholds
- **TTS/STT**: Voice output and input settings
- **Fall Detection**: Accelerometer thresholds and confirmation settings
- **Timelapse**: Frame interval, segment duration, upload settings
- **Location**: GPS port, update intervals, batch settings

## 🐳 Docker Deployment

The project includes Docker support for easy deployment:

```bash
# Build image
docker build -t medispecs-api .

# Run container
docker run -d \
  --name medispecs-api \
  --privileged \
  --device /dev/i2c-1 \
  --device /dev/gpiomem \
  --device /dev/video0 \
  -p 8000:8000 \
  --env-file .env \
  medispecs-api
```

## 📝 Notes

- The backend uses SQLite for local data storage
- All cloud operations go through AWS Lambda API Gateway
- Hardware components require proper GPIO/I2C/Serial permissions
- Camera access may require video group membership
- TTS uses gTTS (requires internet) with pyttsx3 fallback (offline)
- STT uses Vosk (fully offline, no internet required)

## 🤝 Contributing

This project is developed by Pacific KMPP team for the RemindAR smart glass system.

## 📄 License

[Add your license information here]

---

**Built with ❤️ for Alzheimer's patients and their caregivers**

