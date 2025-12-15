"""
Fast TTS Server - Runs on Your Machine
Optimized for real-time phone calls
"""

from flask import Flask, request, send_file, jsonify
from TTS.api import TTS
import uuid
from pathlib import Path
import time
import os

app = Flask(__name__)

OUTPUT_DIR = Path("tts_output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Load TTS once at startup
print("🎤 Loading TTS model...")
start = time.time()
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
print(f"✅ TTS loaded in {time.time() - start:.1f}s")

REFERENCE_VOICE = "reference_voice.wav"


@app.route("/generate", methods=["POST"])
def generate_speech():
    """Generate speech FAST for phone calls"""
    
    try:
        start_time = time.time()
        
        data = request.get_json()
        text = data.get("text", "")
        
        if not text:
            return jsonify({"error": "No text"}), 400
        
        # Keep it short for phone calls (Twilio has 15 second timeout)
        if len(text) > 200:
            text = text[:200]  # Truncate long text
        
        print(f"🎙️  Generating: {text[:50]}...")
        
        audio_id = str(uuid.uuid4())
        output_file = OUTPUT_DIR / f"{audio_id}.wav"
        
        # Generate with your voice
        gen_start = time.time()
        tts.tts_to_file(
            text=text,
            file_path=str(output_file),
            speaker_wav=REFERENCE_VOICE,
            language="en"
        )
        gen_time = time.time() - gen_start
        
        total_time = time.time() - start_time
        print(f"✅ Generated in {gen_time:.1f}s (total: {total_time:.1f}s)")
        
        return send_file(output_file, mimetype="audio/wav")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok", "model": "xtts_v2"})


if __name__ == "__main__":
    print("=" * 80)
    print("🎤 FAST TTS SERVER - Your Machine")
    print("=" * 80)
    print(f"📂 Reference: {REFERENCE_VOICE}")
    print(f"🌐 Server: http://0.0.0.0:5000")
    print("=" * 80)
    
    # For local testing: Flask dev server
    # For Railway: use gunicorn (add to Dockerfile CMD)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)