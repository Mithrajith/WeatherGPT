import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Languages the rest of the app (translator target codes, TTS) actually supports.
# `langdetect` returns ISO codes for many languages we can't act on; anything
# outside this set falls back to whatever deep-translator's `source` reports.
SUPPORTED_LANGUAGES = {"en", "hi", "ta", "te", "kn", "bn"}


class MultilingualSystem:
    """
    A service that handles multilingual translation for LLM interactions.
    It translates user input from any language to English before sending to the LLM,
    and translates the LLM's English response back to the user's original language.
    """

    def __init__(self):
        try:
            from deep_translator import GoogleTranslator
            self._GoogleTranslator = GoogleTranslator
            self._is_available = True
        except ImportError:
            logger.warning("deep-translator package is not installed. Run: pip install deep-translator")
            self._GoogleTranslator = None
            self._is_available = False

        try:
            import langdetect
            self._langdetect = langdetect
        except ImportError:
            logger.warning("langdetect package is not installed. Run: pip install langdetect")
            self._langdetect = None

    def _detect_language(self, text: str) -> Optional[str]:
        """Best-effort language detection via langdetect, ignoring codes we can't act on."""
        if not self._langdetect:
            return None
        try:
            code = self._langdetect.detect(text)
        except Exception:
            return None
        return code if code in SUPPORTED_LANGUAGES else None

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
        # langdetect on the raw text is checked first: it's a dedicated language
        # classifier, so it's more reliable on short queries than trusting
        # deep-translator's `source` (which is really a translation side-effect).
        pre_detected = self._detect_language(text)

        if not self._is_available:
            return text, pre_detected or 'en'

        try:
            translator = self._GoogleTranslator(source='auto', target='en')
            translated = translator.translate(text)
            if not self._looks_like_translation(translated):
                logger.warning("Translation service returned an unusable response; using original text.")
                return text, pre_detected or 'en'
            detected_lang = pre_detected or translator.source
            # deep-translator's auto-detect resolves to the detected code once translate() runs.
            if not detected_lang or detected_lang == 'auto':
                detected_lang = 'en'

            logger.info(f"Translated user input from {detected_lang} to English.")
            return translated, detected_lang
        except Exception as e:
            logger.error(f"Failed to translate user input: {e}")
            return text, pre_detected or 'en'

    @staticmethod
    def _looks_like_translation(text: Optional[str]) -> bool:
        """Reject the upstream's occasional HTML error page masquerading as a result.

        deep-translator's free Google endpoint sometimes returns a "500 Server
        Error" HTML page as if it were a normal translation instead of raising,
        so a truthy non-empty string is not enough to trust it.
        """
        if not text or not text.strip():
            return False
        lowered = text.lower()
        return not any(marker in lowered for marker in ("<html", "server error", "that’s an error", "that's an error"))

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
            translator = self._GoogleTranslator(source='en', target=target_language)
            translated = translator.translate(english_text)
            if not self._looks_like_translation(translated):
                logger.warning("Translation service returned an unusable response; using English text.")
                return english_text
            logger.info(f"Translated LLM response from English to {target_language}.")
            return translated
        except Exception as e:
            logger.error(f"Failed to translate LLM response: {e}")
            return english_text
