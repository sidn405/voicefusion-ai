# Create test_imports.py
import sys

packages = [
    'TTS.api',
    'twilio.rest',
    'twilio.twiml.voice_response',
    'flask',
    'uvicorn',
    'fastapi',
    'librosa',
    'soundfile',
    'torch'
]

print("Testing imports...")
for package in packages:
    try:
        __import__(package)
        print(f"✅ {package}")
    except ImportError as e:
        print(f"❌ {package} - {e}")