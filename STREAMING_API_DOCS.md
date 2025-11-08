# 📹 MediSpecs Streaming API Documentation

## Base URL

**Local Development:**
```
http://localhost:8000
```

**Production (via ngrok):**
```
https://your-ngrok-url.ngrok.io
```

Replace `your-ngrok-url` with your actual ngrok URL (e.g., `abc123.ngrok.io`)

---

## 🔍 Endpoints

### 1. Check Stream Status

**Endpoint:** `GET /stream/status`

**Description:** Check if camera is running and stream is available

**Response Format:** JSON

**Example Request:**
```bash
curl https://your-ngrok-url.ngrok.io/stream/status
```

**Example Response:**
```json
{
  "status": "available",
  "camera_running": true,
  "camera_type": "picamera2",
  "has_frame": true,
  "stream_url": "/stream/live",
  "message": "Camera is ready for streaming"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | "available" or "unavailable" |
| `camera_running` | boolean | Is the camera service active? |
| `camera_type` | string | "picamera2" or "opencv" |
| `has_frame` | boolean | Has at least one frame been captured? |
| `stream_url` | string | Relative URL to the stream endpoint |
| `message` | string | Human-readable status message |

**Use Case:** Call this endpoint before trying to display the stream to check if it's available.

---

### 2. Live Video Stream

**Endpoint:** `GET /stream/live`

**Description:** Live MJPEG video stream from the camera

**Response Format:** `multipart/x-mixed-replace` (MJPEG stream)

**Stream Specifications:**
- **Format:** MJPEG (Motion JPEG)
- **Frame Rate:** 2 FPS (frames per second)
- **Resolution:** 640x480 pixels
- **Quality:** 70% JPEG compression
- **Color Space:** RGB
- **Bandwidth:** ~150-300 KB/s

**Example Request:**
```bash
curl https://your-ngrok-url.ngrok.io/stream/live
```

---

## 🌐 Frontend Integration Examples

### Example 1: HTML (Simplest)

```html
<!DOCTYPE html>
<html>
<head>
    <title>MediSpecs Stream</title>
</head>
<body>
    <h1>Live Camera Feed</h1>
    
    <!-- Direct image tag - browser handles MJPEG automatically -->
    <img src="https://your-ngrok-url.ngrok.io/stream/live" 
         width="640" 
         height="480"
         alt="Live Stream">
</body>
</html>
```

### Example 2: Vanilla JavaScript

```html
<!DOCTYPE html>
<html>
<head>
    <title>MediSpecs Stream</title>
    <style>
        #stream { border: 2px solid #333; border-radius: 10px; }
        .status { padding: 10px; background: #f0f0f0; margin-bottom: 10px; }
        .online { color: green; }
        .offline { color: red; }
    </style>
</head>
<body>
    <div class="status" id="status">Checking status...</div>
    <img id="stream" width="640" height="480" style="display:none;">
    
    <script>
        const BASE_URL = 'https://your-ngrok-url.ngrok.io';
        
        // Check stream status
        async function checkStatus() {
            try {
                const response = await fetch(`${BASE_URL}/stream/status`);
                const data = await response.json();
                
                const statusDiv = document.getElementById('status');
                if (data.camera_running && data.has_frame) {
                    statusDiv.innerHTML = `<span class="online">● Online</span> - ${data.message}`;
                    startStream();
                } else {
                    statusDiv.innerHTML = `<span class="offline">● Offline</span> - Camera not ready`;
                }
            } catch (error) {
                document.getElementById('status').innerHTML = 
                    `<span class="offline">● Error</span> - ${error.message}`;
            }
        }
        
        // Start streaming
        function startStream() {
            const streamImg = document.getElementById('stream');
            streamImg.src = `${BASE_URL}/stream/live`;
            streamImg.style.display = 'block';
            
            // Handle errors
            streamImg.onerror = function() {
                document.getElementById('status').innerHTML = 
                    '<span class="offline">● Error</span> - Stream connection failed';
            };
        }
        
        // Check status on page load
        checkStatus();
        
        // Refresh status every 30 seconds
        setInterval(checkStatus, 30000);
    </script>
</body>
</html>
```

### Example 3: React Component

```jsx
import React, { useState, useEffect } from 'react';

const MediSpecsStream = () => {
    const BASE_URL = 'https://your-ngrok-url.ngrok.io';
    const [status, setStatus] = useState(null);
    const [isOnline, setIsOnline] = useState(false);
    
    useEffect(() => {
        checkStatus();
        const interval = setInterval(checkStatus, 30000);
        return () => clearInterval(interval);
    }, []);
    
    const checkStatus = async () => {
        try {
            const response = await fetch(`${BASE_URL}/stream/status`);
            const data = await response.json();
            setStatus(data);
            setIsOnline(data.camera_running && data.has_frame);
        } catch (error) {
            console.error('Status check failed:', error);
            setIsOnline(false);
        }
    };
    
    return (
        <div>
            <div style={{
                padding: '10px',
                background: isOnline ? '#d4edda' : '#f8d7da',
                color: isOnline ? '#155724' : '#721c24',
                marginBottom: '10px'
            }}>
                {isOnline ? '● Online' : '● Offline'} - 
                {status ? status.message : 'Checking...'}
            </div>
            
            {isOnline && (
                <img 
                    src={`${BASE_URL}/stream/live`}
                    width="640"
                    height="480"
                    alt="Live Stream"
                    style={{ border: '2px solid #333', borderRadius: '10px' }}
                />
            )}
        </div>
    );
};

export default MediSpecsStream;
```

### Example 4: Vue.js Component

```vue
<template>
  <div>
    <div :class="['status', isOnline ? 'online' : 'offline']">
      {{ isOnline ? '● Online' : '● Offline' }} - {{ statusMessage }}
    </div>
    
    <img 
      v-if="isOnline"
      :src="`${baseUrl}/stream/live`"
      width="640"
      height="480"
      alt="Live Stream"
    />
  </div>
</template>

<script>
export default {
  name: 'MediSpecsStream',
  data() {
    return {
      baseUrl: 'https://your-ngrok-url.ngrok.io',
      status: null,
      isOnline: false,
      statusMessage: 'Checking...'
    };
  },
  mounted() {
    this.checkStatus();
    this.interval = setInterval(this.checkStatus, 30000);
  },
  beforeUnmount() {
    clearInterval(this.interval);
  },
  methods: {
    async checkStatus() {
      try {
        const response = await fetch(`${this.baseUrl}/stream/status`);
        const data = await response.json();
        this.status = data;
        this.isOnline = data.camera_running && data.has_frame;
        this.statusMessage = data.message;
      } catch (error) {
        console.error('Status check failed:', error);
        this.isOnline = false;
        this.statusMessage = 'Connection error';
      }
    }
  }
};
</script>

<style scoped>
.status {
  padding: 10px;
  margin-bottom: 10px;
}
.online {
  background: #d4edda;
  color: #155724;
}
.offline {
  background: #f8d7da;
  color: #721c24;
}
</style>
```

### Example 5: Next.js Component

```tsx
'use client';

import { useState, useEffect } from 'react';

interface StreamStatus {
  status: string;
  camera_running: boolean;
  camera_type: string;
  has_frame: boolean;
  stream_url: string;
  message: string;
}

export default function MediSpecsStream() {
  const BASE_URL = 'https://your-ngrok-url.ngrok.io';
  const [status, setStatus] = useState<StreamStatus | null>(null);
  const [isOnline, setIsOnline] = useState(false);

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkStatus = async () => {
    try {
      const response = await fetch(`${BASE_URL}/stream/status`);
      const data: StreamStatus = await response.json();
      setStatus(data);
      setIsOnline(data.camera_running && data.has_frame);
    } catch (error) {
      console.error('Status check failed:', error);
      setIsOnline(false);
    }
  };

  return (
    <div className="stream-container">
      <div className={`status ${isOnline ? 'online' : 'offline'}`}>
        {isOnline ? '● Online' : '● Offline'} - 
        {status ? status.message : 'Checking...'}
      </div>
      
      {isOnline && (
        <img 
          src={`${BASE_URL}/stream/live`}
          width={640}
          height={480}
          alt="Live Stream"
          className="stream-video"
        />
      )}
    </div>
  );
}
```

### Example 6: Mobile App (React Native)

```jsx
import React, { useState, useEffect } from 'react';
import { View, Text, Image, StyleSheet } from 'react-native';

const MediSpecsStream = () => {
  const BASE_URL = 'https://your-ngrok-url.ngrok.io';
  const [isOnline, setIsOnline] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Checking...');
  
  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, []);
  
  const checkStatus = async () => {
    try {
      const response = await fetch(`${BASE_URL}/stream/status`);
      const data = await response.json();
      setIsOnline(data.camera_running && data.has_frame);
      setStatusMessage(data.message);
    } catch (error) {
      setIsOnline(false);
      setStatusMessage('Connection error');
    }
  };
  
  return (
    <View style={styles.container}>
      <View style={[styles.status, isOnline ? styles.online : styles.offline]}>
        <Text>{isOnline ? '● Online' : '● Offline'} - {statusMessage}</Text>
      </View>
      
      {isOnline && (
        <Image 
          source={{ uri: `${BASE_URL}/stream/live` }}
          style={styles.video}
          resizeMode="contain"
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
  },
  status: {
    padding: 10,
    marginBottom: 10,
    borderRadius: 5,
  },
  online: {
    backgroundColor: '#d4edda',
  },
  offline: {
    backgroundColor: '#f8d7da',
  },
  video: {
    width: 640,
    height: 480,
    borderRadius: 10,
  },
});

export default MediSpecsStream;
```

---

## 🔧 Integration Pattern (Recommended)

### Step-by-Step Integration:

1. **Check Status First**
   ```javascript
   const response = await fetch('https://your-ngrok-url.ngrok.io/stream/status');
   const status = await response.json();
   ```

2. **Verify Stream is Available**
   ```javascript
   if (status.camera_running && status.has_frame) {
     // Stream is ready
   }
   ```

3. **Display Stream**
   ```javascript
   <img src="https://your-ngrok-url.ngrok.io/stream/live" />
   ```

4. **Handle Errors**
   ```javascript
   img.onerror = () => {
     console.log('Stream connection failed');
   };
   ```

---

## 🔒 CORS Configuration

CORS is **already enabled** for all origins in your backend:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # All origins allowed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

This means your frontend can call the API from **any domain** without CORS issues.

---

## 🌐 Network Requirements

### For Local Development:
- Backend and frontend must be on the same network
- Backend: `http://localhost:8000`

### For Production (Ngrok):
- Works from anywhere with internet
- Backend: `https://your-ngrok-url.ngrok.io`
- **No VPN or special network required**

---

## 📊 TypeScript Types (for TypeScript projects)

```typescript
// API Response Types

interface StreamStatus {
  status: 'available' | 'unavailable';
  camera_running: boolean;
  camera_type: 'picamera2' | 'opencv';
  has_frame: boolean;
  stream_url: string;
  message: string;
}

// Usage Example
const checkStream = async (baseUrl: string): Promise<StreamStatus> => {
  const response = await fetch(`${baseUrl}/stream/status`);
  return response.json();
};
```

---

## 🐛 Troubleshooting

### Issue: Stream doesn't load

**Solution:**
1. Check status endpoint first: `curl https://your-ngrok-url.ngrok.io/stream/status`
2. Verify `camera_running: true` and `has_frame: true`
3. Check browser console for errors

### Issue: CORS errors

**Solution:**
- Should not happen (CORS is enabled for all origins)
- If you see CORS errors, backend might not be running

### Issue: Slow/laggy stream

**Current Settings:**
- Frame rate: 2 FPS
- Quality: 70%
- Bandwidth: ~150-300 KB/s

**To adjust:** Edit `routers/streaming.py`:
```python
# Lower quality (faster)
encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]

# Higher frame rate (smoother but more bandwidth)
await asyncio.sleep(0.33)  # 3 FPS
```

### Issue: Connection timeout

**Solution:**
- Check if backend is running: `curl https://your-ngrok-url.ngrok.io/health`
- Check ngrok tunnel is active
- Increase timeout in frontend fetch: `fetch(url, { timeout: 30000 })`

---

## 📱 Mobile Considerations

### iOS Safari
- MJPEG streams work natively
- Use `<img>` tag directly

### Android Chrome
- MJPEG streams work natively
- Use `<img>` tag directly

### React Native
- Use `Image` component with URI
- MJPEG support depends on native image libraries

---

## 🔗 Quick Reference

**Base URL:** `https://your-ngrok-url.ngrok.io`

| Endpoint | Method | Response | Purpose |
|----------|--------|----------|---------|
| `/stream/status` | GET | JSON | Check availability |
| `/stream/live` | GET | MJPEG Stream | Video feed |
| `/health` | GET | JSON | Server health |
| `/` | GET | JSON | API info |

---

## 📞 Support

If your frontend team has questions:
1. Check this documentation
2. Test endpoints with curl first
3. Check browser console for errors
4. Verify backend logs

**Happy streaming! 📹**

