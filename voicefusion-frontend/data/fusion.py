from pathlib import Path

# Recreate the fusion.py file after code execution reset
fusion_py = Path("/mnt/data/fusion.py")
fusion_py.write_text(''),
import os
import uuid
import subprocess
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.api.translate_text import load_model

router = APIRouter()

TTS_OUTPUT_DIR = "/home/info/espnet/outputs"
TTS_INFER_SCRIPT = "/home/info/espnet/egs2/vctk/tts1/tts_infer.sh"

class TTSRequest(BaseModel):
    text: str
    source_lang: str = "auto"
    target_lang: str = "en"

@router.post("/translate-and-speak")
async def translate_and_tts(request: TTSRequest):
    try:
        tokenizer, model = load_model(request.source_lang, request.target_lang)
        tokens = tokenizer(request.text, return_tensors="pt", padding=True)
        outputs = model.generate(**tokens)
        translated = tokenizer.decode(outputs[0], skip_special_tokens=True)

        output_filename = f"{uuid.uuid4().hex}.wav"
        output_path = os.path.join(TTS_OUTPUT_DIR, output_filename)

        command = [
            "bash", TTS_INFER_SCRIPT,
            "--text", translated,
            "--output", output_path
        ]
        subprocess.run(command, check=True)

        return {
            "original_text": request.text,
            "translated_text": translated,
            "audio_url": f"/api/tts/audio/{output_filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



