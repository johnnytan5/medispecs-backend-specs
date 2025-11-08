"""
Text-to-Speech Service for MediSpecs
Provides voice output for reminders and face recognition greetings
"""

import asyncio
import threading
from typing import Optional, List, Dict
import time


class TTSService:
    """
    Text-to-Speech service using pyttsx3 (offline)
    
    Features:
    - Offline operation (no internet needed)
    - Female voice for better senior user experience
    - Slower speech rate for clarity
    - Works on both Mac (testing) and Raspberry Pi (Bluetooth)
    - Async support
    - Extensible for future ElevenLabs integration
    """
    
    def __init__(self):
        self.engine = None
        self._initialized = False
        self._lock = threading.Lock()
        
        # Default settings optimized for seniors
        self.default_rate = 130  # Slower: 130 WPM (normal is 150-200)
        self.default_volume = 0.9
        self.prefer_female_voice = True
        
    def initialize(self):
        """Initialize the TTS engine"""
        if self._initialized:
            return True
        
        try:
            import pyttsx3
            
            print("🔊 Initializing Text-to-Speech service...")
            self.engine = pyttsx3.init()
            
            # Set slower speech rate for seniors
            self.engine.setProperty('rate', self.default_rate)
            print(f"   Speech rate: {self.default_rate} WPM (slower for clarity)")
            
            # Set volume
            self.engine.setProperty('volume', self.default_volume)
            print(f"   Volume: {self.default_volume}")
            
            # Try to set female voice
            self._set_female_voice()
            
            self._initialized = True
            print("✅ Text-to-Speech initialized successfully")
            
            return True
            
        except ImportError:
            print("⚠️  pyttsx3 not installed. Install with: pip install pyttsx3")
            print("   On Raspberry Pi, also run: sudo apt-get install espeak")
            self._initialized = False
            return False
            
        except Exception as e:
            print(f"⚠️  TTS initialization failed: {e}")
            print("   Voice output will be disabled")
            self._initialized = False
            return False
    
    def _set_female_voice(self):
        """Set female voice if available"""
        if not self.engine:
            return
        
        try:
            voices = self.engine.getProperty('voices')
            
            # Try to find female voice
            female_voice = None
            for voice in voices:
                voice_name = voice.name.lower()
                voice_id = voice.id.lower()
                
                # Look for female voice markers
                if any(marker in voice_name or marker in voice_id 
                       for marker in ['female', 'woman', 'girl', 'samantha', 'victoria', 'karen']):
                    female_voice = voice.id
                    print(f"   Selected voice: {voice.name} (female)")
                    break
            
            # If no explicit female found, try to pick a voice that sounds female
            if not female_voice and voices:
                # On Mac: voices[0] is usually male, voices[1] is usually female
                # On Linux: depends on espeak installation
                if len(voices) > 1:
                    female_voice = voices[1].id
                    print(f"   Selected voice: {voices[1].name}")
                else:
                    female_voice = voices[0].id
                    print(f"   Using default voice: {voices[0].name}")
            
            if female_voice:
                self.engine.setProperty('voice', female_voice)
            
        except Exception as e:
            print(f"   Could not set female voice: {e}")
            print("   Using default system voice")
    
    @property
    def is_available(self) -> bool:
        """Check if TTS is available"""
        return self._initialized and self.engine is not None
    
    def speak(self, text: str, rate: Optional[int] = None, volume: Optional[float] = None):
        """
        Speak text using TTS (blocking)
        
        Args:
            text: Text to speak
            rate: Speech rate in words per minute (default: 130)
            volume: Volume level 0.0 to 1.0 (default: 0.9)
        """
        if not self.is_available:
            print(f"🔇 TTS not available (would say: '{text}')")
            return
        
        with self._lock:
            try:
                # Set custom rate if provided
                if rate is not None:
                    self.engine.setProperty('rate', rate)
                
                # Set custom volume if provided
                if volume is not None:
                    self.engine.setProperty('volume', volume)
                
                # Speak the text
                print(f"🔊 Speaking: '{text}'")
                self.engine.say(text)
                self.engine.runAndWait()
                
                # Reset to defaults
                if rate is not None:
                    self.engine.setProperty('rate', self.default_rate)
                if volume is not None:
                    self.engine.setProperty('volume', self.default_volume)
                    
            except Exception as e:
                print(f"❌ TTS error: {e}")
    
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
        List available voices
        
        Returns:
            List of voice dictionaries with id, name, and languages
        """
        if not self.is_available:
            return []
        
        try:
            voices = self.engine.getProperty('voices')
            voice_list = []
            
            for voice in voices:
                voice_info = {
                    'id': voice.id,
                    'name': voice.name,
                    'languages': voice.languages if hasattr(voice, 'languages') else [],
                }
                voice_list.append(voice_info)
            
            return voice_list
            
        except Exception as e:
            print(f"❌ Error listing voices: {e}")
            return []
    
    def set_voice(self, voice_id: str):
        """
        Set voice by ID
        
        Args:
            voice_id: Voice ID from list_voices()
        """
        if not self.is_available:
            return False
        
        try:
            self.engine.setProperty('voice', voice_id)
            print(f"✅ Voice changed to: {voice_id}")
            return True
        except Exception as e:
            print(f"❌ Error setting voice: {e}")
            return False
    
    def set_rate(self, rate: int):
        """
        Set speech rate
        
        Args:
            rate: Words per minute (50-300, recommended 100-150 for seniors)
        """
        if not self.is_available:
            return
        
        self.default_rate = max(50, min(300, rate))
        self.engine.setProperty('rate', self.default_rate)
        print(f"✅ Speech rate set to: {self.default_rate} WPM")
    
    def set_volume(self, volume: float):
        """
        Set volume
        
        Args:
            volume: Volume level 0.0 to 1.0
        """
        if not self.is_available:
            return
        
        self.default_volume = max(0.0, min(1.0, volume))
        self.engine.setProperty('volume', self.default_volume)
        print(f"✅ Volume set to: {self.default_volume}")
    
    def stop(self):
        """Stop current speech"""
        if self.is_available:
            try:
                self.engine.stop()
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
                'engine': 'none',
                'error': 'TTS not initialized'
            }
        
        try:
            current_voice = self.engine.getProperty('voice')
            voices = self.engine.getProperty('voices')
            
            # Find current voice name
            current_voice_name = 'Unknown'
            for voice in voices:
                if voice.id == current_voice:
                    current_voice_name = voice.name
                    break
            
            return {
                'available': True,
                'engine': 'pyttsx3',
                'rate': self.default_rate,
                'volume': self.default_volume,
                'current_voice': current_voice_name,
                'current_voice_id': current_voice,
                'voices_count': len(voices)
            }
        except Exception as e:
            return {
                'available': True,
                'engine': 'pyttsx3',
                'error': str(e)
            }


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

