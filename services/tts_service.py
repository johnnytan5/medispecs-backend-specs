"""
Text-to-Speech Service for MediSpecs
Provides voice output for reminders and face recognition greetings

Primary Engine: gTTS (Google TTS - high quality, requires internet)
Fallback Engine: pyttsx3 (offline, basic quality)
"""

import asyncio
import threading
from typing import Optional, List, Dict
import time
import os
import tempfile


class TTSService:
    """
    Hybrid Text-to-Speech service with quality fallback
    
    Primary: gTTS (Google TTS - high quality, requires internet)
    Fallback: pyttsx3 (offline, basic quality)
    
    Features:
    - High quality online voice (gTTS)
    - Automatic offline fallback (pyttsx3)
    - Female voice preference
    - Slower speech rate for seniors
    - Works on Mac and Raspberry Pi
    - Async support
    - Extensible for future ElevenLabs integration
    """
    
    def __init__(self):
        # pyttsx3 engine (offline fallback)
        self.pyttsx3_engine = None
        self.pyttsx3_available = False
        
        # gTTS availability (online, high quality)
        self.gtts_available = False
        
        self._initialized = False
        self._lock = threading.Lock()
        
        # Default settings optimized for seniors
        self.default_rate = 130  # Slower: 130 WPM (normal is 150-200)
        self.default_volume = 0.9
        self.prefer_female_voice = True
        
        # Track which engine was last used
        self.last_engine_used = None
        
    def initialize(self):
        """Initialize both TTS engines (gTTS primary, pyttsx3 fallback)"""
        if self._initialized:
            return True
        
        print("🔊 Initializing Text-to-Speech service...")
        
        # Try to initialize gTTS (online, high quality)
        try:
            from gtts import gTTS
            import pygame
            
            # Test if gTTS works (requires internet)
            test_tts = gTTS(text="test", lang='en', slow=False)
            self.gtts_available = True
            print("   ✅ gTTS (Google) available - HIGH QUALITY mode")
            
            # Initialize pygame for audio playback
            pygame.mixer.init()
            
        except ImportError:
            print("   ⚠️  gTTS not installed (pip install gtts pygame)")
            self.gtts_available = False
        except Exception as e:
            print(f"   ⚠️  gTTS not available (offline or error: {e})")
            self.gtts_available = False
        
        # Try to initialize pyttsx3 (offline fallback)
        try:
            import pyttsx3
            
            self.pyttsx3_engine = pyttsx3.init()
            
            # Set slower speech rate for seniors
            self.pyttsx3_engine.setProperty('rate', self.default_rate)
            self.pyttsx3_engine.setProperty('volume', self.default_volume)
            
            # Try to set female voice
            self._set_female_voice()
            
            self.pyttsx3_available = True
            print("   ✅ pyttsx3 (offline) available - FALLBACK mode")
            
        except ImportError:
            print("   ⚠️  pyttsx3 not installed (pip install pyttsx3)")
            print("      On Raspberry Pi: sudo apt-get install espeak")
            self.pyttsx3_available = False
        except Exception as e:
            print(f"   ⚠️  pyttsx3 initialization failed: {e}")
            self.pyttsx3_available = False
        
        # Check if at least one engine is available
        if self.gtts_available or self.pyttsx3_available:
            self._initialized = True
            
            if self.gtts_available:
                print("✅ Text-to-Speech ready (using gTTS for best quality)")
            else:
                print("✅ Text-to-Speech ready (offline mode only)")
            
            print(f"   Speech optimized for seniors: slower rate, female voice")
            return True
        else:
            print("❌ No TTS engines available - voice output disabled")
            self._initialized = False
            return False
    
    def _set_female_voice(self):
        """Set female voice for pyttsx3 (offline engine)"""
        if not self.pyttsx3_engine:
            return
        
        try:
            voices = self.pyttsx3_engine.getProperty('voices')
            
            # Try to find female voice
            female_voice = None
            for voice in voices:
                voice_name = voice.name.lower()
                voice_id = voice.id.lower()
                
                # Look for female voice markers
                if any(marker in voice_name or marker in voice_id 
                       for marker in ['female', 'woman', 'girl', 'samantha', 'victoria', 'karen']):
                    female_voice = voice.id
                    print(f"   pyttsx3 voice: {voice.name} (female)")
                    break
            
            # If no explicit female found, try to pick a voice that sounds female
            if not female_voice and voices:
                # On Mac: voices[0] is usually male, voices[1] is usually female
                # On Linux: depends on espeak installation
                if len(voices) > 1:
                    female_voice = voices[1].id
                    print(f"   pyttsx3 voice: {voices[1].name}")
                else:
                    female_voice = voices[0].id
                    print(f"   pyttsx3 voice: {voices[0].name} (default)")
            
            if female_voice:
                self.pyttsx3_engine.setProperty('voice', female_voice)
            
        except Exception as e:
            print(f"   Could not set female voice: {e}")
            print("   Using default system voice")
    
    @property
    def is_available(self) -> bool:
        """Check if TTS is available"""
        return self._initialized and (self.gtts_available or self.pyttsx3_available)
    
    def _speak_with_gtts(self, text: str) -> bool:
        """
        Speak using gTTS (Google TTS - high quality)
        
        Returns:
            bool: True if successful, False if failed
        """
        try:
            from gtts import gTTS
            import pygame
            
            # Create temp file for audio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_file = fp.name
            
            # Generate speech (slow=True for slower, clearer speech for seniors)
            tts = gTTS(text=text, lang='en', slow=True)
            tts.save(temp_file)
            
            # Play the audio
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
            
            self.last_engine_used = 'gtts'
            return True
            
        except Exception as e:
            print(f"   ⚠️  gTTS failed: {e}")
            return False
    
    def _speak_with_pyttsx3(self, text: str, rate: Optional[int] = None, volume: Optional[float] = None) -> bool:
        """
        Speak using pyttsx3 (offline fallback)
        
        Returns:
            bool: True if successful, False if failed
        """
        if not self.pyttsx3_available:
            return False
        
        try:
            # Set custom rate if provided
            if rate is not None:
                self.pyttsx3_engine.setProperty('rate', rate)
            
            # Set custom volume if provided
            if volume is not None:
                self.pyttsx3_engine.setProperty('volume', volume)
            
            # Speak the text
            self.pyttsx3_engine.say(text)
            self.pyttsx3_engine.runAndWait()
            
            # Reset to defaults
            if rate is not None:
                self.pyttsx3_engine.setProperty('rate', self.default_rate)
            if volume is not None:
                self.pyttsx3_engine.setProperty('volume', self.default_volume)
            
            self.last_engine_used = 'pyttsx3'
            return True
            
        except Exception as e:
            print(f"   ⚠️  pyttsx3 failed: {e}")
            return False
    
    def speak(self, text: str, rate: Optional[int] = None, volume: Optional[float] = None):
        """
        Speak text using TTS with automatic quality fallback (blocking)
        
        Priority:
        1. gTTS (Google - high quality, online)
        2. pyttsx3 (basic quality, offline)
        
        Args:
            text: Text to speak
            rate: Speech rate in words per minute (default: 130) - only for pyttsx3
            volume: Volume level 0.0 to 1.0 (default: 0.9) - only for pyttsx3
        """
        if not self.is_available:
            print(f"🔇 TTS not available (would say: '{text}')")
            return
        
        with self._lock:
            print(f"🔊 Speaking: '{text}'")
            
            # Try gTTS first (best quality)
            if self.gtts_available:
                print(f"   Using gTTS (Google, high quality)...")
                success = self._speak_with_gtts(text)
                if success:
                    return
                else:
                    print(f"   gTTS failed, falling back to offline mode...")
            
            # Fallback to pyttsx3 (offline)
            if self.pyttsx3_available:
                print(f"   Using pyttsx3 (offline)...")
                success = self._speak_with_pyttsx3(text, rate, volume)
                if success:
                    return
            
            print(f"❌ All TTS engines failed")
    
    async def speak_async(self, text: str, rate: Optional[int] = None, volume: Optional[float] = None):
        """
        Speak text using TTS (non-blocking, async)
        
        Args:
            text: Text to speak
            rate: Speech rate in words per minute (default: 130)
            volume: Volume level 0.0 to 1.0 (default: 0.9)
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.speak, text, rate, volume)
    
    def list_voices(self) -> List[Dict[str, str]]:
        """
        List available voices (pyttsx3 only, gTTS uses Google's voice)
        
        Returns:
            List of voice dictionaries with id, name, and languages
        """
        voice_list = []
        
        # gTTS info
        if self.gtts_available:
            voice_list.append({
                'id': 'gtts-en',
                'name': 'Google TTS (English, High Quality)',
                'languages': ['en'],
                'engine': 'gtts'
            })
        
        # pyttsx3 voices
        if self.pyttsx3_available:
            try:
                voices = self.pyttsx3_engine.getProperty('voices')
                
                for voice in voices:
                    voice_info = {
                        'id': voice.id,
                        'name': voice.name,
                        'languages': voice.languages if hasattr(voice, 'languages') else [],
                        'engine': 'pyttsx3'
                    }
                    voice_list.append(voice_info)
            except Exception as e:
                print(f"❌ Error listing pyttsx3 voices: {e}")
        
        return voice_list
    
    def set_voice(self, voice_id: str):
        """
        Set voice by ID (pyttsx3 only)
        
        Args:
            voice_id: Voice ID from list_voices()
        """
        if not self.pyttsx3_available:
            return False
        
        try:
            self.pyttsx3_engine.setProperty('voice', voice_id)
            print(f"✅ pyttsx3 voice changed to: {voice_id}")
            return True
        except Exception as e:
            print(f"❌ Error setting voice: {e}")
            return False
    
    def set_rate(self, rate: int):
        """
        Set speech rate (pyttsx3 only, gTTS uses slow=True)
        
        Args:
            rate: Words per minute (50-300, recommended 100-150 for seniors)
        """
        if not self.pyttsx3_available:
            return
        
        self.default_rate = max(50, min(300, rate))
        self.pyttsx3_engine.setProperty('rate', self.default_rate)
        print(f"✅ pyttsx3 speech rate set to: {self.default_rate} WPM")
    
    def set_volume(self, volume: float):
        """
        Set volume (pyttsx3 only)
        
        Args:
            volume: Volume level 0.0 to 1.0
        """
        if not self.pyttsx3_available:
            return
        
        self.default_volume = max(0.0, min(1.0, volume))
        self.pyttsx3_engine.setProperty('volume', self.default_volume)
        print(f"✅ pyttsx3 volume set to: {self.default_volume}")
    
    def stop(self):
        """Stop current speech"""
        try:
            # Stop pygame (gTTS)
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except:
            pass
        
        # Stop pyttsx3
        if self.pyttsx3_available:
            try:
                self.pyttsx3_engine.stop()
            except:
                pass
    
    def get_info(self) -> Dict[str, any]:
        """
        Get TTS service information
        
        Returns:
            Dictionary with TTS status and configuration
        """
        if not self.is_available:
            return {
                'available': False,
                'engines': [],
                'error': 'TTS not initialized'
            }
        
        info = {
            'available': True,
            'engines': [],
            'primary_engine': 'gtts' if self.gtts_available else 'pyttsx3',
            'last_used': self.last_engine_used or 'none'
        }
        
        # gTTS info
        if self.gtts_available:
            info['engines'].append({
                'name': 'gtts',
                'status': 'available',
                'quality': 'high',
                'requires_internet': True,
                'description': 'Google Text-to-Speech'
            })
        
        # pyttsx3 info
        if self.pyttsx3_available:
            try:
                current_voice = self.pyttsx3_engine.getProperty('voice')
                voices = self.pyttsx3_engine.getProperty('voices')
                
                # Find current voice name
                current_voice_name = 'Unknown'
                for voice in voices:
                    if voice.id == current_voice:
                        current_voice_name = voice.name
                        break
                
                info['engines'].append({
                    'name': 'pyttsx3',
                    'status': 'available',
                    'quality': 'basic',
                    'requires_internet': False,
                    'description': 'Offline TTS (espeak/sapi5)',
                    'rate': self.default_rate,
                    'volume': self.default_volume,
                    'current_voice': current_voice_name,
                    'voices_count': len(voices)
                })
            except Exception as e:
                info['engines'].append({
                    'name': 'pyttsx3',
                    'status': 'error',
                    'error': str(e)
                })
        
        return info


# Global service instance
_tts_instance: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get the global TTS service instance"""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TTSService()
        _tts_instance.initialize()
    return _tts_instance


# Convenience functions for quick usage
def speak(text: str, rate: Optional[int] = None, volume: Optional[float] = None):
    """Quick function to speak text"""
    tts = get_tts_service()
    tts.speak(text, rate, volume)


async def speak_async(text: str, rate: Optional[int] = None, volume: Optional[float] = None):
    """Quick async function to speak text"""
    tts = get_tts_service()
    await tts.speak_async(text, rate, volume)

