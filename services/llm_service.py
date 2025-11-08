"""
LLM Service for MediSpecs
Handles conversation with OpenAI GPT for voice command processing

NOTE: Ruby provides information and clarification only.
Ruby CANNOT execute actions, create reminders, or control devices.
This is a conversational assistant only.

VISION: Ruby can also analyze images with GPT-4o Vision API.
"""

import asyncio
import time
import base64
from typing import Optional
import os
import numpy as np


class LLMService:
    """
    LLM service for processing voice commands with OpenAI GPT
    
    Features:
    - Conversational AI (no context, one-off responses)
    - Senior-friendly language (clear, concise, simple words)
    - Fallback handling for offline/errors
    - Response via TTS
    """
    
    def __init__(self):
        self.api_key: Optional[str] = None
        self.model: str = "gpt-3.5-turbo"
        self.system_prompt: str = ""
        self.is_available: bool = False
        self.fallback_message: str = "I am not connected to internet right now"
        
    def initialize(self, api_key: str, model: str, system_prompt: str):
        """
        Initialize LLM service with API credentials
        
        Args:
            api_key: OpenAI API key
            model: Model to use (e.g., "gpt-3.5-turbo")
            system_prompt: System instruction for Ruby's personality
        """
        print("🤖 Initializing LLM service...")
        
        if not api_key or api_key == "":
            print("   ⚠️  No OpenAI API key provided")
            print("   Add OPENAI_API_KEY to .env file")
            self.is_available = False
            return False
        
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        
        # Test import
        try:
            import openai
            print(f"   ✅ OpenAI library installed")
        except ImportError:
            print("   ❌ OpenAI library not installed")
            print("   Install with: pip install openai")
            self.is_available = False
            return False
        
        print(f"   Model: {self.model}")
        print(f"   System prompt: {self.system_prompt[:60]}...")
        print("✅ LLM service initialized")
        
        self.is_available = True
        return True
    
    async def process_command(self, command: str) -> str:
        """
        Process voice command with LLM and return response
        
        Args:
            command: Transcribed voice command from user
            
        Returns:
            LLM response text (to be spoken via TTS)
        """
        if not self.is_available:
            print("⚠️  LLM not available, using fallback")
            return self.fallback_message
        
        if not command or command.strip() == "":
            return "I didn't catch that. Could you repeat?"
        
        print(f"\n{'='*60}")
        print(f"🤖 [LLM] Processing command: '{command}'")
        print(f"{'='*60}")
        
        try:
            import openai
            
            # Set API key
            openai.api_key = self.api_key
            
            # Create messages (no context, stateless)
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": command}
            ]
            
            # Call OpenAI API
            start_time = time.time()
            
            response = await asyncio.to_thread(
                openai.chat.completions.create,
                model=self.model,
                messages=messages,
                max_tokens=150,  # Keep responses short
                temperature=0.7,
                timeout=10  # 10 second timeout
            )
            
            elapsed = time.time() - start_time
            
            # Extract response text
            response_text = response.choices[0].message.content.strip()
            
            print(f"✅ [LLM] Response received ({elapsed:.2f}s)")
            print(f"💬 Ruby: '{response_text}'")
            print(f"{'='*60}\n")
            
            return response_text
            
        except ImportError:
            print("❌ [LLM] OpenAI library not installed")
            return self.fallback_message
            
        except openai.AuthenticationError:
            print("❌ [LLM] Invalid API key")
            return "Sorry, I'm having authentication issues"
            
        except openai.RateLimitError:
            print("❌ [LLM] Rate limit exceeded")
            return "Sorry, I'm being used too much right now"
            
        except openai.APIConnectionError:
            print("❌ [LLM] No internet connection")
            return self.fallback_message
            
        except asyncio.TimeoutError:
            print("❌ [LLM] Request timed out")
            return "Sorry, that took too long"
            
        except Exception as e:
            print(f"❌ [LLM] Error: {e}")
            return "Sorry, I had trouble understanding that"
    
    async def process_vision_command(self, image_frame, command: str, vision_model: str, vision_system_prompt: str) -> str:
        """
        Process vision command with image and text using GPT-4o Vision API
        
        Args:
            image_frame: numpy array (BGR or RGB format from OpenCV)
            command: Transcribed voice command from user
            vision_model: Model to use (e.g., "gpt-4o")
            vision_system_prompt: System instruction for vision tasks
            
        Returns:
            LLM response text (to be spoken via TTS)
        """
        if not self.is_available:
            print("⚠️  LLM not available, using fallback")
            from config import VISION_FALLBACK_MESSAGE
            return VISION_FALLBACK_MESSAGE
        
        if image_frame is None:
            print("⚠️  No image frame available")
            from config import VISION_FALLBACK_MESSAGE
            return VISION_FALLBACK_MESSAGE
        
        if not command or command.strip() == "":
            return "I'm looking, but I didn't hear your question. Could you repeat?"
        
        print(f"\n{'='*60}")
        print(f"👁️  [VISION] Processing command: '{command}'")
        print(f"{'='*60}")
        
        try:
            import cv2
            import openai
            
            # Set API key
            openai.api_key = self.api_key
            
            # Convert image frame to base64
            print("   📸 Encoding image...")
            
            # Ensure frame is in RGB format (OpenCV uses BGR)
            if len(image_frame.shape) == 3 and image_frame.shape[2] == 3:
                # Check if it's BGR (from OpenCV) - convert to RGB
                # Face detection service stores in RGB already, but just in case
                image_rgb = image_frame  # Assume already RGB from face_detection_service
            else:
                print("   ⚠️  Unexpected image format")
                from config import VISION_FALLBACK_MESSAGE
                return VISION_FALLBACK_MESSAGE
            
            # Encode to JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
            _, buffer = cv2.imencode('.jpg', image_rgb, encode_param)
            
            # Convert to base64
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            image_size_kb = len(image_base64) / 1024
            print(f"   ✅ Image encoded: {image_size_kb:.1f} KB")
            
            # Create messages with vision
            messages = [
                {"role": "system", "content": vision_system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "low"  # Low detail = cheaper, faster, sufficient for most cases
                            }
                        },
                        {
                            "type": "text",
                            "text": command
                        }
                    ]
                }
            ]
            
            # Call OpenAI Vision API
            start_time = time.time()
            print(f"   🤖 Calling {vision_model}...")
            
            response = await asyncio.to_thread(
                openai.chat.completions.create,
                model=vision_model,
                messages=messages,
                max_tokens=200,  # Allow slightly longer responses for vision
                temperature=0.7,
                timeout=15  # 15 second timeout (vision takes longer)
            )
            
            elapsed = time.time() - start_time
            
            # Extract response text
            response_text = response.choices[0].message.content.strip()
            
            print(f"✅ [VISION] Response received ({elapsed:.2f}s)")
            print(f"💬 Ruby: '{response_text}'")
            print(f"{'='*60}\n")
            
            return response_text
            
        except ImportError as e:
            print(f"❌ [VISION] Missing library: {e}")
            from config import VISION_FALLBACK_MESSAGE
            return VISION_FALLBACK_MESSAGE
            
        except openai.AuthenticationError:
            print("❌ [VISION] Invalid API key")
            return "Sorry, I'm having authentication issues"
            
        except openai.RateLimitError:
            print("❌ [VISION] Rate limit exceeded")
            return "Sorry, I'm being used too much right now"
            
        except openai.APIConnectionError:
            print("❌ [VISION] No internet connection")
            from config import VISION_FALLBACK_MESSAGE
            return VISION_FALLBACK_MESSAGE
            
        except asyncio.TimeoutError:
            print("❌ [VISION] Request timed out")
            return "Sorry, that took too long"
            
        except Exception as e:
            print(f"❌ [VISION] Error: {e}")
            return "Sorry, I had trouble seeing that"
    
    async def speak_response(self, response_text: str):
        """
        Speak LLM response using TTS service
        
        Args:
            response_text: Text to speak
        """
        try:
            from services.tts_service import get_tts_service
            from config import TTS_ENABLED
            
            if TTS_ENABLED:
                tts = get_tts_service()
                if tts.is_available:
                    print(f"🔊 [TTS] Speaking response...")
                    await tts.speak_async(response_text)
                else:
                    print("⚠️  TTS not available")
            else:
                print("⚠️  TTS disabled, response not spoken")
                
        except Exception as e:
            print(f"❌ [TTS] Error speaking response: {e}")
    
    async def process_and_speak(self, command: str):
        """
        Complete flow: Process command with LLM and speak response
        
        Args:
            command: Voice command from user
        """
        # Get LLM response
        response = await self.process_command(command)
        
        # Speak response
        await self.speak_response(response)
    
    async def process_vision_and_speak(self, image_frame, command: str, vision_model: str, vision_system_prompt: str):
        """
        Complete flow: Process vision command with image and speak response
        
        Args:
            image_frame: Camera frame (numpy array)
            command: Voice command from user
            vision_model: Model to use (e.g., "gpt-4o")
            vision_system_prompt: System instruction for vision
        """
        # Get vision response
        response = await self.process_vision_command(image_frame, command, vision_model, vision_system_prompt)
        
        # Speak response
        await self.speak_response(response)
    
    def get_status(self):
        """Get LLM service status"""
        return {
            'available': self.is_available,
            'model': self.model,
            'has_api_key': self.api_key is not None and self.api_key != "",
            'system_prompt': self.system_prompt
        }


# Global service instance
_llm_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMService()
    return _llm_instance

