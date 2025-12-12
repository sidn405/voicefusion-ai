from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import MarianTokenizer, MarianMTModel
import subprocess
import uuid
import os
import sys
from app.api import translate_text, stt, clone
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from fusion import router as fusion_router, tts
from routes import chat, translate
from fusion.tts import synthesize


app = FastAPI(title="VoiceFusion AI")

sys.path.append("/home/info/espnet")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # only allow your React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount each feature as a separate route
app.include_router(tts.router, prefix="/api/tts")
app.include_router(stt.router, prefix="/api/stt")
app.include_router(clone.router, prefix="/api/clone")
app.include_router(translate_text.router, prefix="/api/translate")
app.include_router(chat.router, prefix="/api/chat")
app.include_router(translate.router)
app.include_router(fusion_router, prefix="/api")

class TTSRequest(BaseModel):
    text: str
    source_lang: str  # e.g., "en"
    target_lang: str  # e.g., "fr"

class TranslateInput(BaseModel):
    text: str
    source_lang: str
    target_lang: str

def load_translation_model(src, tgt):
    model_name = f"Helsinki-NLP/opus-mt-{src}-{tgt}"
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    return tokenizer, model

@app.get("/")
def root():
    return {"message": "welcome to VoiceFusion AI API"}

@app.post("/translate-then-speak/")
async def translate_then_speak(payload: TranslateInput):
    translated_text = translate_text(payload.source_lang, payload.target_lang, payload.text)
    wav = synthesize(translated_text["translated_text"])
    # Save or stream the audio response


@app.post("/translate_tts")
def translate_and_tts(req: TTSRequest):
    try:
        # Step 1: Translate
        tokenizer, model = load_translation_model(req.source_lang, req.target_lang)
        tokens = tokenizer(req.text, return_tensors="pt", padding=True)
        outputs = model.generate(**tokens)
        translated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Step 2: Save translated text for ESPnet TTS
        unique_id = str(uuid.uuid4())[:8]
        input_path = f"/tmp/input_{unique_id}.txt"
        with open(input_path, "w") as f:
            f.write(translated_text)

        # Step 3: Call ESPnet TTS inference script (adjust as needed)
        output_path = f"/tmp/output_{unique_id}.wav"
        subprocess.run(["python3", "tts.py", "--text_path", input_path, "--output_path", output_path], check=True)

        return {"status": "success", "translated_text": translated_text, "audio_path": output_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



