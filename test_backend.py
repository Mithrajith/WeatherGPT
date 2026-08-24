import os
from dotenv import load_dotenv
from src.multilingual_system.translation_manager import MultilingualSystem
from src.weather_gpt.llm_service import LLMService
from src.weather_gpt.voice_service import VoiceService

def test_pipeline():
    print("=== Testing WeatherGPT Multilingual Backend ===")
    
    # 1. Load env and init services
    load_dotenv()
    translator = MultilingualSystem()
    llm = LLMService()
    voice = VoiceService()
    
    # 2. Mock a user input in Tamil ("What is the weather in Chennai?")
    # Tamil for "What is the weather in Chennai?": "சென்னையில் வானிலை எப்படி இருக்கிறது?"
    tamil_input = "சென்னையில் வானிலை எப்படி இருக்கிறது?"
    
    print(f"\\n[USER - Tamil]: {tamil_input}")
    
    # 3. Translate to English
    english_prompt, detected_lang = translator.process_user_input(tamil_input)
    print(f"\\n[SYSTEM - Detected Language]: {detected_lang}")
    print(f"[SYSTEM - Translated to LLM]: {english_prompt}")
    
    # 4. Get LLM response
    english_response = llm.get_weather_response(english_prompt)
    print(f"\\n[LLM - English Response]: {english_response}")
    
    # 5. Translate back to Tamil
    final_response = translator.process_llm_response(english_response, detected_lang)
    print(f"\\n[SYSTEM - Translated back to {detected_lang}]: {final_response}")
    
    # 6. Optional: Test Text to Speech
    print("\\nTesting TTS Generation...")
    audio_bytes = voice.text_to_speech(final_response, detected_lang)
    if audio_bytes:
        print(f"Success! Generated {len(audio_bytes)} bytes of audio.")
    else:
        print("Failed to generate audio or gTTS not available.")

if __name__ == "__main__":
    test_pipeline()
