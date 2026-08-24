import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MultilingualSystem:
    """
    A service that handles multilingual translation for LLM interactions.
    It translates user input from any language to English before sending to the LLM,
    and translates the LLM's English response back to the user's original language.
    """
    
    def __init__(self):
        try:
            from googletrans import Translator
            self.translator = Translator()
            self._is_available = True
        except ImportError:
            logger.warning("googletrans package is not installed. Run: pip install googletrans==4.0.0-rc1")
            self.translator = None
            self._is_available = False

    def process_user_input(self, text: str) -> tuple[str, str]:
        """
        Detects the user's language and translates the text to English.
        
        Args:
            text: The original user input in any language.
            
        Returns:
            A tuple containing:
                - The translated English text (to send to LLM)
                - The detected language code (e.g., 'ta' for Tamil, 'hi' for Hindi)
        """
        if not self._is_available:
            return text, 'en'
            
        try:
            # Translate to English and capture the detected source language
            result = self.translator.translate(text, dest='en')
            detected_lang = result.src
            
            logger.info(f"Translated user input from {detected_lang} to English.")
            return result.text, detected_lang
        except Exception as e:
            logger.error(f"Failed to translate user input: {e}")
            return text, 'en'

    def process_llm_response(self, english_text: str, target_language: str) -> str:
        """
        Translates the LLM's English response back to the user's language.
        
        Args:
            english_text: The response from the LLM in English.
            target_language: The language code to translate the response into.
            
        Returns:
            The translated text in the user's language.
        """
        if not self._is_available or target_language == 'en':
            return english_text
            
        try:
            result = self.translator.translate(english_text, src='en', dest=target_language)
            logger.info(f"Translated LLM response from English to {target_language}.")
            return result.text
        except Exception as e:
            logger.error(f"Failed to translate LLM response: {e}")
            return english_text
