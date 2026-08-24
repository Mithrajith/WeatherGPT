import os
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .llm_service import LLMService
from .voice_service import VoiceService
from src.multilingual_system.translation_manager import MultilingualSystem

# Load environment variables
load_dotenv()

app = FastAPI(title="WeatherGPT API")

# Add CORS so the frontend can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Services
translator = MultilingualSystem()
llm = LLMService()
voice = VoiceService()

@app.post("/chat")
async def chat_endpoint(user_text: str = Form(...)):
    """
    1. Receives user text in any language.
    2. Translates to English.
    3. Fetches response from LLM.
    4. Translates response back to the user's language.
    """
    # 1. Translate user's input to English
    english_prompt, detected_lang = translator.process_user_input(user_text)
    
    # 2. Get LLM Response
    english_response = llm.get_weather_response(english_prompt)
    
    # 3. Translate back to user's language
    final_response = translator.process_llm_response(english_response, target_language=detected_lang)
    
    return JSONResponse({
        "original_text": user_text,
        "detected_language": detected_lang,
        "english_prompt": english_prompt,
        "english_response": english_response,
        "final_response": final_response
    })

@app.post("/speech-to-text")
async def speech_to_text(audio_file: UploadFile = File(...), language: str = Form("en")):
    """
    Receives an audio file (e.g., from frontend recording) and transcribes it to text.
    """
    audio_bytes = await audio_file.read()
    transcribed_text = voice.speech_to_text(audio_bytes, language=language)
    return JSONResponse({"text": transcribed_text})

@app.post("/text-to-speech")
async def text_to_speech(text: str = Form(...), language: str = Form("en")):
    """
    Receives text and generates an audio file speaking the text.
    """
    audio_bytes = voice.text_to_speech(text, language=language)
    if not audio_bytes:
        return JSONResponse({"error": "Failed to generate speech"}, status_code=500)
        
    return Response(content=audio_bytes, media_type="audio/mpeg")

@app.get("/")
def health_check():
    return {"status": "ok", "service": "WeatherGPT Multilingual Backend"}
