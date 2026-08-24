import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class LLMService:
    """
    Handles interactions with the LLM (Gemini) to process weather-related queries.
    """
    def __init__(self):
        # We try to initialize the Gemini client
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY is not set in the environment.")
            self.client = None
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
            self.model_name = "gemini-2.5-flash"
        except ImportError:
            logger.error("google-genai package not installed.")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.client = None

    def get_weather_response(self, prompt: str) -> str:
        """
        Takes an English prompt, fetches weather logic (mocked here), and returns an English response.
        """
        if not self.client:
            # Fallback if API key is not set
            return "I'm sorry, my AI backend is not configured yet. (Missing GEMINI_API_KEY)"

        # System instructions to make it behave like WeatherGPT
        system_instruction = (
            "You are WeatherGPT, a helpful and concise weather assistant. "
            "When a user asks for weather, provide a helpful and conversational response. "
            "Since you do not have live tools connected yet, use your best general knowledge "
            "or politely inform them if you can't fetch real-time data for specific small towns. "
            "Keep the answer concise and friendly."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.7
                }
            )
            return response.text
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            return "I'm sorry, I encountered an error while trying to process your request."
