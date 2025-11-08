"""
LLM Service for MediSpecs
Handles conversation with OpenAI GPT for voice command processing

NOTE: Ruby provides information and clarification only.
Ruby CANNOT execute actions, create reminders, or control devices.
This is a conversational assistant only.
"""

import asyncio
import time
from typing import Optional
import os


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

