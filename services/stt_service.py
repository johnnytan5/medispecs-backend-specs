"""
Speech-to-Text Service for MediSpecs
Provides wake word detection ("Hey Ruby") and voice command transcription

Uses Vosk for offline, real-time speech recognition on Raspberry Pi
"""

import asyncio
import json
import queue
import threading
from typing import Optional, Callable
import time


class STTService:
    """
    Speech-to-Text service with wake word detection
    
    Features:
    - Continuous listening for "Hey Ruby" wake word
    - Command recording after wake word detected
    - Offline operation using Vosk
    - USB microphone support
    - Background service (runs continuously)
    - Prepared for OpenAI LLM integration
    """
    
    def __init__(self):
        self.is_running = False
        self.is_listening = False
        self.task: Optional[asyncio.Task] = None
        
        # Vosk components
        self.model = None
        self.recognizer = None
        
        # Audio components
        self.audio_queue = queue.Queue()
        self.sample_rate = 16000
        self.device_index = None
        
        # Wake word settings
        self.wake_word = "hey ruby"
        self.wake_word_detected = False
        self.command_timeout = 5  # seconds to record command
        
        # Callbacks for integration
        self.on_wake_word_callback: Optional[Callable] = None
        self.on_command_callback: Optional[Callable] = None
        
    def initialize(self, model_path: str, device_index: Optional[int] = None):
        """
        Initialize Vosk model and audio device
        
        Args:
            model_path: Path to Vosk model directory (e.g., "vosk-model-en-us-0.22")
            device_index: Audio device index (None = default)
        """
        print("🎤 Initializing Speech-to-Text service...")
        
        try:
            from vosk import Model, KaldiRecognizer
            import sounddevice as sd
            
            # Initialize Vosk model
            print(f"   Loading Vosk model from: {model_path}")
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            print("   ✅ Vosk model loaded successfully")
            
            # Set audio device
            self.device_index = device_index
            if device_index is not None:
                sd.default.device = device_index
                print(f"   Audio device set to index: {device_index}")
            else:
                print("   Using default audio device")
            
            # Test audio device
            devices = sd.query_devices()
            
            # Handle different return types from sd.default.device
            # Can be: int, tuple, or _InputOutputPair object
            try:
                if hasattr(sd.default.device, 'input'):
                    # It's an _InputOutputPair object (input, output)
                    current_device = sd.default.device.input
                elif isinstance(sd.default.device, tuple):
                    # It's a tuple (input_device, output_device)
                    current_device = sd.default.device[0]
                else:
                    # It's an integer (device index)
                    current_device = sd.default.device
                
                device_info = devices[current_device]
                print(f"   Microphone: {device_info['name']}")
            except Exception as e:
                print(f"   Microphone: Default (could not get name: {e})")
            
            print(f"   Sample rate: {self.sample_rate} Hz")
            
            print("✅ Speech-to-Text initialized successfully")
            print(f"   Wake word: '{self.wake_word}'")
            print(f"   Command timeout: {self.command_timeout}s")
            return True
            
        except ImportError as e:
            print("❌ Required packages not installed!")
            print("   Install with: pip install vosk sounddevice")
            print(f"   Error: {e}")
            return False
            
        except Exception as e:
            print(f"❌ STT initialization failed: {e}")
            print("   Make sure:")
            print("   1. Vosk model is downloaded and path is correct")
            print("   2. USB microphone is connected")
            print("   3. Audio permissions are granted")
            return False
    
    def list_audio_devices(self):
        """List all available audio input devices"""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            
            print("\n📱 Available Audio Devices:")
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    print(f"   [{i}] {device['name']}")
                    print(f"       Channels: {device['max_input_channels']}, Sample Rate: {device['default_samplerate']}")
            
            return devices
        except Exception as e:
            print(f"❌ Error listing devices: {e}")
            return []
    
    async def start(self):
        """Start the STT service (continuous wake word detection)"""
        if self.is_running:
            print("⚠️  STT service is already running")
            return
        
        if not self.model:
            print("❌ STT not initialized. Call initialize() first")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._listening_loop())
        
        print("▶️  STT service started - listening for wake word...")
    
    async def stop(self):
        """Stop the STT service"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        print("⏹️  STT service stopped")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream (runs in separate thread)"""
        if status:
            print(f"⚠️  Audio status: {status}")
        
        # Add audio data to queue
        self.audio_queue.put(bytes(indata))
    
    async def _listening_loop(self):
        """Main listening loop - continuously listens for wake word"""
        print("🔄 STT listening loop started")
        
        try:
            import sounddevice as sd
            
            # Start audio stream
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=8000,
                dtype='int16',
                channels=1,
                callback=self._audio_callback
            ):
                print(f"🎧 Listening for '{self.wake_word}'...")
                self.is_listening = True
                
                while self.is_running:
                    try:
                        # Get audio data from queue
                        data = self.audio_queue.get(timeout=1)
                        
                        # Process with Vosk
                        if self.recognizer.AcceptWaveform(data):
                            result = json.loads(self.recognizer.Result())
                            text = result.get('text', '').lower().strip()
                            
                            if text:
                                # Log all transcribed text with timestamp
                                import time
                                timestamp = time.strftime("%H:%M:%S")
                                print(f"🎤 [{timestamp}] [TRANSCRIBED] '{text}'")
                                
                                # Check for wake word
                                if not self.wake_word_detected and self.wake_word in text:
                                    print(f"\n" + "="*60)
                                    print(f"🔔 WAKE WORD DETECTED: '{self.wake_word}'")
                                    print(f"="*60)
                                    self.wake_word_detected = True
                                    
                                    # Respond with TTS greeting
                                    await self._respond_to_wake_word()
                                    
                                    # Callback notification
                                    if self.on_wake_word_callback:
                                        try:
                                            await self.on_wake_word_callback()
                                        except:
                                            pass
                                    
                                    # Record command
                                    command = await self._record_command()
                                    
                                    # Reset for next wake word
                                    self.wake_word_detected = False
                                    print(f"\n🎧 Listening for '{self.wake_word}'...")
                                    print("="*60 + "\n")
                        
                        # Allow other tasks to run
                        await asyncio.sleep(0.01)
                        
                    except queue.Empty:
                        # No audio data, continue
                        await asyncio.sleep(0.1)
                    
                    except Exception as e:
                        print(f"❌ Error in listening loop: {e}")
                        await asyncio.sleep(1)
        
        except asyncio.CancelledError:
            print("🔄 STT listening loop cancelled")
        except Exception as e:
            print(f"❌ Fatal error in listening loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_listening = False
    
    async def _respond_to_wake_word(self):
        """Respond to wake word with TTS greeting"""
        try:
            from services.tts_service import get_tts_service
            from config import TTS_ENABLED
            
            if TTS_ENABLED:
                tts = get_tts_service()
                if tts.is_available:
                    greeting = "Hey, I am Ruby. How can I help you?"
                    print(f"🔊 Ruby: '{greeting}'")
                    
                    # Speak greeting (fire-and-forget)
                    asyncio.create_task(tts.speak_async(greeting))
        except Exception as e:
            print(f"⚠️  Could not speak greeting: {e}")
    
    async def _record_command(self):
        """Record and transcribe command after wake word detected"""
        print(f"🎙️  Recording command (timeout: {self.command_timeout}s)...")
        
        # Clear recognizer state
        self.recognizer = None
        from vosk import KaldiRecognizer
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
        
        # Clear audio queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except:
                break
        
        # Record for timeout duration
        start_time = time.time()
        command_parts = []
        
        print("   (Speak now...)")
        
        while time.time() - start_time < self.command_timeout:
            try:
                data = self.audio_queue.get(timeout=0.5)
                
                # Get partial results for real-time feedback
                partial_result = json.loads(self.recognizer.PartialResult())
                partial_text = partial_result.get('partial', '')
                if partial_text:
                    print(f"   💬 Hearing: '{partial_text}'", end='\r')
                
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    if text:
                        print(f"   ✓ Captured: '{text}'")
                        command_parts.append(text)
                
                await asyncio.sleep(0.01)
                
            except queue.Empty:
                continue
        
        # Get final result
        final_result = json.loads(self.recognizer.FinalResult())
        final_text = final_result.get('text', '').strip()
        if final_text:
            command_parts.append(final_text)
        
        # Combine all parts
        full_command = ' '.join(command_parts).strip()
        
        print("\n" + "-"*60)
        if full_command:
            print(f"✅ [COMMAND] '{full_command}'")
            print("-"*60)
            
            # Log to console for debugging
            print(f"📝 Logged command: {full_command}")
            
            # Process with LLM and speak response
            try:
                from services.llm_service import get_llm_service
                from config import LLM_ENABLED
                
                if LLM_ENABLED:
                    llm = get_llm_service()
                    if llm.is_available:
                        # Send to LLM and speak response
                        await llm.process_and_speak(full_command)
                    else:
                        print("⚠️  LLM not available, command logged only")
                else:
                    print("⚠️  LLM disabled, command logged only")
            except Exception as e:
                print(f"❌ Error processing with LLM: {e}")
            
            # Callback with command (for additional custom handling)
            if self.on_command_callback:
                try:
                    await self.on_command_callback(full_command)
                except Exception as e:
                    print(f"❌ Error in command callback: {e}")
        else:
            print("⚠️  [NO COMMAND] Silence or unclear audio")
            print("-"*60)
        
        return full_command
    
    async def test_listen(self, duration: int = 5) -> str:
        """
        Test function - manually record and transcribe audio
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            Transcribed text
        """
        print(f"🎙️  Test recording for {duration}s...")
        
        if not self.model:
            return "Error: STT not initialized"
        
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer
            
            # Create fresh recognizer for test
            test_recognizer = KaldiRecognizer(self.model, self.sample_rate)
            
            # Record audio
            print("   Recording...")
            audio_data = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype='int16'
            )
            sd.wait()
            
            # Process audio
            print("   Transcribing...")
            audio_bytes = audio_data.tobytes()
            
            # Process in chunks
            chunk_size = 8000
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i+chunk_size]
                test_recognizer.AcceptWaveform(chunk)
            
            # Get final result
            result = json.loads(test_recognizer.FinalResult())
            text = result.get('text', '').strip()
            
            print(f"\n{'='*60}")
            print(f"✅ [TEST TRANSCRIPTION] '{text}'")
            print(f"{'='*60}\n")
            
            # Log for debugging
            print(f"📝 Test result: {text}")
            
            return text
            
        except Exception as e:
            print(f"❌ Test recording failed: {e}")
            return f"Error: {str(e)}"
    
    def set_wake_word_callback(self, callback: Callable):
        """Set callback function to be called when wake word is detected"""
        self.on_wake_word_callback = callback
    
    def set_command_callback(self, callback: Callable):
        """Set callback function to be called with transcribed command"""
        self.on_command_callback = callback
    
    def get_status(self):
        """Get STT service status"""
        return {
            'initialized': self.model is not None,
            'running': self.is_running,
            'listening': self.is_listening,
            'wake_word': self.wake_word,
            'command_timeout': self.command_timeout,
            'sample_rate': self.sample_rate,
            'device_index': self.device_index
        }


# Global service instance
_stt_instance: Optional[STTService] = None


def get_stt_service() -> STTService:
    """Get the global STT service instance"""
    global _stt_instance
    if _stt_instance is None:
        _stt_instance = STTService()
    return _stt_instance

