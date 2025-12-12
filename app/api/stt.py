from fastapi.responses import FileResponse
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from fusion.tts import TTS_OUTPUT_DIR, synthesize_speech

router = APIRouter()

class TTSRequest(BaseModel):
    text: str
    voice: str
    language: str = "en"  # Optional for future multilingual support

@router.post("/tts")
def tts_generate(payload: TTSRequest):
    try:
        output_path = synthesize_speech(payload.text, payload.voice, payload.language)
        return {"audio_path": output_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    file_path = os.path.join(TTS_OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(file_path, media_type="audio/wav")

