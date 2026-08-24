import io
import logging
from typing import Optional

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VoiceService:
    """
    Handles Speech-to-Text (STT) and Text-to-Speech (TTS) logic.
    """
    def __init__(self):
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.sr_available = True
        except ImportError:
            logger.warning("speech_recognition package not available.")
            self.sr_available = False

        try:
            from gtts import gTTS
            self.gtts_available = True
        except ImportError:
            logger.warning("gTTS package not available.")
            self.gtts_available = False

    def speech_to_text(self, audio_file_bytes: bytes, language: str = 'en') -> str:
        """
        Converts uploaded audio file (bytes) into text.
        Requires SpeechRecognition.
        """
        if not self.sr_available:
            return "Speech recognition is not available."

        import speech_recognition as sr
        
        try:
            # Convert incoming audio (likely webm from browser) to WAV using pydub
            from pydub import AudioSegment
            import io
            
            audio_file = io.BytesIO(audio_file_bytes)
            audio_segment = AudioSegment.from_file(audio_file)
            
            # Export to a new BytesIO as WAV
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")
            wav_io.seek(0)
            
            with sr.AudioFile(wav_io) as source:
                audio = self.recognizer.record(source)

            # Using Google Web Speech API for free STT
            text = self.recognizer.recognize_google(audio, language=language)
            logger.info(f"Transcribed audio: {text}")
            return text
        except sr.UnknownValueError:
            logger.error("Speech Recognition could not understand audio")
            return "Could not understand audio"
        except sr.RequestError as e:
            logger.error(f"Could not request results from Google Speech Recognition service; {e}")
            return "Error calling STT service"
        except Exception as e:
            logger.error(f"STT error: {e}")
            return f"Error processing audio: {e}"

    def text_to_speech(self, text: str, language: str = 'en') -> Optional[bytes]:
        """
        Converts text into spoken audio bytes.
        Requires gTTS.
        """
        if not self.gtts_available or not text:
            return None

        from gtts import gTTS
        try:
            # Generate the TTS
            tts = gTTS(text=text, lang=language, slow=False)
            
            # Save it to a byte stream
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            
            # Get the bytes
            audio_bytes = fp.getvalue()
            return audio_bytes
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None
