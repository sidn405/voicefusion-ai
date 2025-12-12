from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import torch
import torch.serialization
import soundfile as sf
import uuid
import os

# Add safe globals for XTTS
try:
    from TTS.tts.configs.xtts_config import XttsConfig
    torch.serialization.add_safe_globals([XttsConfig])
except ImportError:
    pass  # Skip if TTS not yet loaded

# Initialize router and app
router = APIRouter()
app = FastAPI()

# Configuration
TTS_OUTPUT_DIR = os.getenv("TTS_OUTPUT_DIR", "./tts_output")
os.makedirs(TTS_OUTPUT_DIR, exist_ok=True)

class TTSRequest(BaseModel):
    text: str
    lang: str = "en"
    voice: str = "default"

# Global TTS model cache
tts_model = None

def load_tts_model():
    """Load and cache TTS model"""
    global tts_model
    if tts_model is None:
        try:
            from TTS.api import TTS
            tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
            print("✅ TTS model loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load TTS model: {e}")
            raise
    return tts_model

def run_tts_inference(text: str, speaker_wav: str = None) -> str:
    """
    Run TTS inference and return path to .wav file.
    
    Args:
        text: Text to synthesize
        speaker_wav: Optional path to reference audio for voice cloning
    """
    model = load_tts_model()
    
    # Generate unique output path
    out_path = os.path.join(TTS_OUTPUT_DIR, f"tts_{uuid.uuid4().hex}.wav")
    
    try:
        if speaker_wav and os.path.exists(speaker_wav):
            # Voice cloning
            model.tts_to_file(
                text=text,
                file_path=out_path,
                speaker_wav=speaker_wav,
                language="en"
            )
        else:
            # Regular TTS
            model.tts_to_file(
                text=text,
                file_path=out_path,
                language="en"
            )
        
        print(f"✅ Generated audio: {out_path}")
        return out_path
        
    except Exception as e:
        print(f"❌ TTS inference failed: {e}")
        raise

@router.post("/synthesize")
@app.post("/synthesize")
async def synthesize_text(request: TTSRequest):
    """Synthesize text to speech"""
    try:
        audio_path = run_tts_inference(request.text)
        filename = os.path.basename(audio_path)
        
        return {
            "status": "success",
            "audio_url": f"/api/tts/audio/{filename}",
            "audio_path": audio_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/synthesize_cloned")
@app.post("/synthesize_cloned")
async def synthesize_cloned(request: TTSRequest, speaker_wav: str):
    """Synthesize text with voice cloning"""
    try:
        if not os.path.exists(speaker_wav):
            raise HTTPException(status_code=404, detail="Speaker reference audio not found")
        
        audio_path = run_tts_inference(request.text, speaker_wav)
        filename = os.path.basename(audio_path)
        
        return {
            "status": "success",
            "audio_url": f"/api/tts/audio/{filename}",
            "audio_path": audio_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audio/{filename}")
@app.get("/audio/{filename}")
async def get_audio_file(filename: str):
    """Serve generated audio file"""
    file_path = os.path.join(TTS_OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/wav")

@router.post("/tts")
@app.post("/tts")
async def generate_tts(request: TTSRequest):
    """Generate TTS audio"""
    try:
        audio_path = run_tts_inference(request.text)
        filename = os.path.basename(audio_path)
        
        return {
            "status": "success",
            "audio_url": f"/api/tts/audio/{filename}",
            "text": request.text,
            "language": request.lang
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Include router in app
app.include_router(router, prefix="/api/tts")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting TTS API server...")
    print(f"📁 Output directory: {TTS_OUTPUT_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8000)