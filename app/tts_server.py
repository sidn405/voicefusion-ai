"""
Lightweight TTS Server - Railway Compatible
Uses pyttsx3 (no ML models, instant deployment)
Perfect for LawBot phone calls
"""

from flask import Flask, request, send_file, jsonify
import pyttsx3
import uuid
from pathlib import Path
import time
import os

app = Flask(__name__)

OUTPUT_DIR = Path("tts_output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Initialize TTS engine (super fast, no downloads)
print("🎤 Initializing lightweight TTS...")
start = time.time()
engine = pyttsx3.init()

# Configure voice settings for professional sound
voices = engine.getProperty('voices')
# Use female voice if available (index 1 on most systems)
if len(voices) > 1:
    engine.setProperty('voice', voices[1].id)  # Female voice
engine.setProperty('rate', 150)  # Speed (150 = natural pace)
engine.setProperty('volume', 0.9)  # Volume

print(f"✅ TTS ready in {time.time() - start:.1f}s")


@app.route("/generate", methods=["POST"])
def generate_speech():
    """Generate speech INSTANTLY (< 1 second)"""
    
    try:
        start_time = time.time()
        
        data = request.get_json()
        text = data.get("text", "")
        
        if not text:
            return jsonify({"error": "No text"}), 400
        
        # Keep reasonable length for phone calls
        if len(text) > 500:
            text = text[:500]
        
        print(f"🎙️ Generating: {text[:50]}...")
        
        audio_id = str(uuid.uuid4())
        output_file = OUTPUT_DIR / f"{audio_id}.wav"
        
        # Generate speech (super fast!)
        gen_start = time.time()
        engine.save_to_file(text, str(output_file))
        engine.runAndWait()
        gen_time = time.time() - gen_start
        
        total_time = time.time() - start_time
        print(f"✅ Generated in {gen_time:.2f}s (total: {total_time:.2f}s)")
        
        return send_file(output_file, mimetype="audio/wav")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({
        "status": "ok", 
        "engine": "pyttsx3",
        "type": "lightweight",
        "deployment": "railway-ready"
    })


if __name__ == "__main__":
    print("=" * 80)
    print("🎤 LIGHTWEIGHT TTS SERVER - Railway Ready")
    print("=" * 80)
    print(f"⚡ Engine: pyttsx3 (no ML models)")
    print(f"🚀 Speed: < 1 second per request")
    print(f"💰 Size: < 100MB (vs 2GB+ for ML models)")
    print(f"🌐 Server: http://0.0.0.0:5000")
    print("=" * 80)
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)