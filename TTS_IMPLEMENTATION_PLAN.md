# 🔊 Text-to-Speech (TTS) Implementation Plan

## 📋 Overview

Add voice output to MediSpecs so seniors can **hear** reminders and face recognition greetings, not just see them on the OLED display.

---

## 🎯 Goals

1. **Speak reminders** when they trigger (e.g., "Time to take your medication")
2. **Speak greetings** when face is recognized (e.g., "Hello Johnny!")
3. **Work offline** on Raspberry Pi (no internet dependency)
4. **Optional high-quality voices** when internet is available (AWS Polly)
5. **Easy to integrate** with existing OLED display code

---

## 🔧 Recommended Library: **Hybrid Approach**

### Primary: `pyttsx3` (Offline) ⭐ RECOMMENDED

**Pros:**
- ✅ Works **offline** (no internet needed)
- ✅ Very lightweight (~50KB)
- ✅ Fast (<100ms latency)
- ✅ Uses `espeak` on Raspberry Pi (pre-installed)
- ✅ Multiple voices available
- ✅ Adjustable speed and volume
- ✅ Python-only, no external services

**Cons:**
- ⚠️ Voice quality is "robotic" (but clear and understandable)
- ⚠️ Limited voice variety

**Installation:**
```bash
pip install pyttsx3
sudo apt-get install espeak espeak-ng  # Usually pre-installed on Raspberry Pi OS
```

### Secondary: `Amazon Polly` (Online, Optional)

**Pros:**
- ✅ **High-quality natural voices**
- ✅ You're already using AWS (Rekognition)
- ✅ Multiple languages and voices
- ✅ Neural TTS available
- ✅ Very natural sounding

**Cons:**
- ⚠️ Requires internet
- ⚠️ Costs money (but cheap: $4 per 1M characters)
- ⚠️ Higher latency (~500ms)

**Installation:**
```bash
pip install boto3
```

---

## 🏗️ Architecture

### Service Structure

```
services/
├── tts_service.py          # NEW - Text-to-Speech service
└── oled_display.py         # EXISTING - Visual display

routers/
├── tts.py                  # NEW - TTS API endpoints
├── display.py              # EXISTING
└── reminders.py            # MODIFIED - Add TTS calls

services/
├── reminder_scheduler.py   # MODIFIED - Add TTS to reminders
└── face_detection_service.py  # MODIFIED - Add TTS to greetings
```

### Integration Points

```
┌─────────────────────────────────────────────────────┐
│              Trigger Events                          │
├─────────────────────────────────────────────────────┤
│  • Reminder fires                                    │
│  • Face recognized                                   │
│  • Manual API call                                   │
└────────────────┬────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────┐
│           TTS Service (tts_service.py)               │
├─────────────────────────────────────────────────────┤
│  1. Check if TTS enabled                            │
│  2. Try pyttsx3 (offline, fast)                     │
│  3. Fallback to Polly if configured                 │
│  4. Handle errors gracefully                         │
└────────────────┬────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────┐
│              Audio Output                            │
├─────────────────────────────────────────────────────┤
│  • Raspberry Pi speaker/headphone jack              │
│  • Bluetooth speaker                                 │
│  • USB audio device                                  │
└─────────────────────────────────────────────────────┘
```

---

## 📁 Files to Create/Modify

### NEW Files:

1. **`services/tts_service.py`**
   - Main TTS service class
   - pyttsx3 integration
   - Optional AWS Polly integration
   - Helper functions
   - Voice configuration

2. **`routers/tts.py`**
   - API endpoints for testing TTS
   - `/tts/speak` - Speak text
   - `/tts/status` - Check TTS availability
   - `/tts/voices` - List available voices

### MODIFIED Files:

3. **`services/reminder_scheduler.py`**
   - Add TTS call when reminder triggers
   - Speak reminder message after OLED display

4. **`services/face_detection_service.py`**
   - Add TTS call when face recognized
   - Speak greeting after OLED display

5. **`config.py`**
   - Add TTS configuration options
   - Enable/disable TTS
   - Voice selection
   - Volume/speed settings

6. **`main.py`**
   - Register TTS router
   - Initialize TTS service on startup

7. **`requirements.txt`**
   - Add `pyttsx3`
   - Add `boto3` (optional, for Polly)

---

## 🎨 API Design

### Endpoints

#### 1. Speak Text
```http
POST /tts/speak
Content-Type: application/json

{
  "text": "Hello Johnny! Time to take your medication.",
  "voice": "default",
  "speed": 150,
  "volume": 0.9
}

Response:
{
  "status": "success",
  "message": "Text spoken successfully",
  "method": "pyttsx3",
  "duration_ms": 2500
}
```

#### 2. Check Status
```http
GET /tts/status

Response:
{
  "enabled": true,
  "available": true,
  "engine": "pyttsx3",
  "polly_available": false,
  "voices_count": 4,
  "current_voice": "english-us"
}
```

#### 3. List Voices
```http
GET /tts/voices

Response:
{
  "voices": [
    {"id": "english-us", "name": "English (US)", "gender": "male"},
    {"id": "english-uk", "name": "English (UK)", "gender": "female"}
  ]
}
```

---

## 🔧 Helper Functions

### Core Functions

```python
# Simple API
tts_service.speak("Hello!")

# With options
tts_service.speak(
    text="Hello Johnny!",
    voice="english-us",
    speed=150,  # Words per minute (default: 150)
    volume=0.9  # 0.0 to 1.0 (default: 0.9)
)

# Async version
await tts_service.speak_async("Hello!")

# Check availability
if tts_service.is_available():
    tts_service.speak("TTS is ready!")

# List voices
voices = tts_service.list_voices()

# Change voice
tts_service.set_voice("english-uk")

# Set volume
tts_service.set_volume(0.8)

# Set speed
tts_service.set_speed(160)
```

### Integration Functions

```python
# For reminders (will add to reminder_scheduler.py)
def speak_reminder(reminder_text: str):
    """Speak a reminder message"""
    tts = get_tts_service()
    if tts.is_available():
        tts.speak(reminder_text)

# For face recognition (will add to face_detection_service.py)
def speak_greeting(name: str, relationship: str = None):
    """Speak a greeting when face is recognized"""
    tts = get_tts_service()
    if tts.is_available():
        if relationship:
            tts.speak(f"Hello {name}! Your {relationship} is here.")
        else:
            tts.speak(f"Hello {name}!")
```

---

## ⚙️ Configuration (config.py)

```python
# Text-to-Speech Configuration
TTS_ENABLED = True                    # Enable/disable TTS
TTS_ENGINE = "pyttsx3"                # "pyttsx3" or "polly"
TTS_VOICE = "default"                 # Voice ID (engine-specific)
TTS_SPEED = 150                       # Words per minute (100-200)
TTS_VOLUME = 0.9                      # Volume (0.0 to 1.0)

# AWS Polly (optional)
TTS_POLLY_ENABLED = False             # Enable AWS Polly as fallback
TTS_POLLY_VOICE = "Joanna"           # Polly voice name
TTS_POLLY_ENGINE = "neural"          # "standard" or "neural"

# Audio Output
TTS_AUDIO_DEVICE = "default"         # Audio device (or specific device)
```

---

## 🔄 Integration Examples

### Example 1: Reminder with Voice

**Before:**
```python
# reminder_scheduler.py (line ~110)
oled.display_reminder(
    message=display_message,
    font_size=14,
    should_blink=True,
    display_time=10
)
```

**After:**
```python
# reminder_scheduler.py
oled.display_reminder(
    message=display_message,
    font_size=14,
    should_blink=True,
    display_time=10
)

# Add voice output
from services.tts_service import get_tts_service
tts = get_tts_service()
if tts.is_available():
    tts.speak(f"Reminder: {reminder.title}")
```

### Example 2: Face Recognition Greeting

**Before:**
```python
# face_detection_service.py (line ~352)
oled.display_reminder(
    message=display_message,
    font_size=14,
    should_blink=True,
    display_time=10
)
```

**After:**
```python
# face_detection_service.py
oled.display_reminder(
    message=display_message,
    font_size=14,
    should_blink=True,
    display_time=10
)

# Add voice output
from services.tts_service import get_tts_service
tts = get_tts_service()
if tts.is_available():
    greeting = f"Hello {name}!"
    if relationship:
        greeting += f" Your {relationship} is here."
    tts.speak(greeting)
```

---

## 🧪 Testing Strategy

### Manual Testing
```bash
# Test TTS directly
curl -X POST http://localhost:8000/tts/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello! This is a test."}'

# Check status
curl http://localhost:8000/tts/status

# List voices
curl http://localhost:8000/tts/voices
```

### Integration Testing
1. Trigger a reminder → Should speak + display
2. Recognize a face → Should greet with voice + display
3. Test with TTS disabled → Should work silently
4. Test with no audio device → Should fail gracefully

---

## 📦 Dependencies

### Required
```txt
pyttsx3==2.90              # Offline TTS
```

### Optional (for AWS Polly)
```txt
boto3==1.34.0              # AWS SDK (already have for Rekognition)
```

### System Dependencies (Raspberry Pi)
```bash
sudo apt-get install espeak espeak-ng alsa-utils
```

---

## 🎛️ Voice Options

### pyttsx3 Voices (Raspberry Pi)
- `english-us` - American English (male)
- `english-uk` - British English (female)
- `english` - Generic English
- And others depending on espeak installation

### AWS Polly Voices (if enabled)
- `Joanna` - American English (female, neural)
- `Matthew` - American English (male, neural)
- `Ivy` - American English (child, neural)
- 50+ voices in multiple languages

---

## 🚀 Implementation Steps

### Phase 1: Core TTS Service (Day 1)
1. Create `services/tts_service.py`
2. Implement pyttsx3 integration
3. Add configuration to `config.py`
4. Test basic speech output

### Phase 2: API Endpoints (Day 1)
1. Create `routers/tts.py`
2. Add `/tts/speak`, `/tts/status`, `/tts/voices`
3. Test with curl/Postman

### Phase 3: Integration (Day 2)
1. Modify `reminder_scheduler.py` - Add TTS to reminders
2. Modify `face_detection_service.py` - Add TTS to greetings
3. Test end-to-end

### Phase 4: Optional Enhancements (Day 3)
1. Add AWS Polly support (optional)
2. Add voice selection UI
3. Add volume/speed controls
4. Add TTS history/logs

---

## ⚠️ Considerations

### Audio Hardware
- **Raspberry Pi has audio jack** - Should work out of box
- **USB speakers** - Need to configure ALSA
- **Bluetooth speakers** - Need Bluetooth pairing
- **HDMI audio** - Need to configure audio output

### Performance
- pyttsx3 is **fast** (~50-100ms to start speaking)
- No significant CPU impact
- Can speak while doing other tasks (async)

### Volume Control
```bash
# Test audio output
speaker-test -t wav -c 2

# Adjust volume
alsamixer

# Set volume via command
amixer set Master 80%
```

### Reliability
- **Offline mode** ensures reminders always speak
- **Graceful degradation** if TTS fails
- **Never block** other operations

---

## 🎉 Benefits for Seniors

1. **Multi-modal output** - See + hear reminders
2. **Better for visually impaired** - Audio backup
3. **More engaging** - Voice is more noticeable than screen
4. **Familiar interface** - Speaking is natural
5. **Hands-free** - Don't need to look at screen

---

## 💰 Cost Analysis

### pyttsx3 (Offline)
- **Cost:** $0 (free, open source)
- **Speed:** Very fast (~50ms)
- **Quality:** Basic but clear
- **Reliability:** High (no internet needed)

### AWS Polly (Online, Optional)
- **Cost:** $4 per 1M characters
- **Typical usage:** ~100 reminders/day = ~$0.01/month
- **Speed:** Slower (~500ms)
- **Quality:** Excellent (neural voices)
- **Reliability:** Requires internet

**Recommendation:** Start with pyttsx3, add Polly later if needed.

---

## 📋 Implementation Checklist

- [ ] Create `services/tts_service.py`
- [ ] Create `routers/tts.py`
- [ ] Update `config.py` with TTS settings
- [ ] Update `requirements.txt`
- [ ] Modify `reminder_scheduler.py`
- [ ] Modify `face_detection_service.py`
- [ ] Register TTS router in `main.py`
- [ ] Test audio output on Raspberry Pi
- [ ] Test with reminders
- [ ] Test with face recognition
- [ ] Create documentation
- [ ] Add to README

---

## 🤔 Questions for You

Before I implement, please confirm:

1. **Library choice:** 
   - ✅ Use pyttsx3 (offline, free)?
   - ❓ Want AWS Polly too (optional, paid)?

2. **Integration points:**
   - ✅ Speak when reminders trigger?
   - ✅ Speak when face recognized?
   - ❓ Any other places to add voice?

3. **Voice preference:**
   - Default male/female voice?
   - Speed: Normal (150 WPM) or faster/slower?

4. **Audio output:**
   - Using Pi's audio jack?
   - External speakers?
   - Bluetooth?

5. **Optional features:**
   - Want voice selection API?
   - Want to queue multiple TTS messages?
   - Want TTS history/logs?

---

## 📝 Summary

**Recommendation:** Implement **pyttsx3** as primary TTS engine with clean service architecture that allows adding AWS Polly later if needed.

**Timeline:** 1-2 days for full implementation and testing

**Risk:** Low - TTS is non-critical feature that won't break existing functionality

**Value:** High - Significantly improves accessibility and user experience for seniors

---

## ✅ Next Steps

**If you approve this plan, I will:**

1. Install pyttsx3 dependency
2. Create TTS service with helper functions
3. Create API endpoints for testing
4. Integrate with reminders and face recognition
5. Add configuration options
6. Test everything
7. Provide usage documentation

**Ready to proceed?** Let me know if you want any changes to this plan! 🚀

