"""
Quick Test - XTTS Voice Cloning
Run this after fixing PyTorch version
"""

import sys

print("🔍 Checking setup...")

# Check Python
print(f"✅ Python: {sys.version.split()[0]}")

# Check PyTorch
try:
    import torch
    print(f"✅ PyTorch: {torch.__version__}")
    
    # Check if version is compatible
    major, minor = torch.__version__.split('.')[:2]
    if int(major) == 2 and int(minor) <= 5:
        print("   ✅ Version compatible with TorchCodec")
    else:
        print(f"   ⚠️ Version {torch.__version__} may have issues")
        print("   Recommended: 2.5.1 or lower")
except ImportError:
    print("❌ PyTorch not installed")
    sys.exit(1)

# Check TTS
try:
    from TTS.api import TTS
    print("✅ TTS: Installed")
except ImportError:
    print("❌ TTS not installed")
    print("   Install: pip install TTS")
    sys.exit(1)

# Check FFmpeg
import subprocess
try:
    result = subprocess.run(['ffmpeg', '-version'], 
                          capture_output=True, text=True)
    ffmpeg_version = result.stdout.split('\n')[0]
    print(f"✅ FFmpeg: {ffmpeg_version.split()[2]}")
except FileNotFoundError:
    print("❌ FFmpeg not found in PATH")
    sys.exit(1)

# Check reference audio
import os
if os.path.exists("reference_voice.wav"):
    size = os.path.getsize("reference_voice.wav") / 1024
    print(f"✅ Reference audio: reference_voice.wav ({size:.1f} KB)")
else:
    print("⚠️ Reference audio not found: reference_voice.wav")
    print("   Please add a reference audio file")

print("\n" + "="*50)
print("🎯 Setup Status:")

# Try loading XTTS
try:
    print("🔄 Testing XTTS model loading...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
    print("✅ XTTS v2 loaded successfully!")
    
    # Try generating test audio
    if os.path.exists("reference_voice.wav"):
        print("\n🔄 Testing voice cloning...")
        tts.tts_to_file(
            text="This is a quick test.",
            file_path="quick_test.wav",
            speaker_wav="reference_voice.wav",
            language="en"
        )
        print("✅ Voice cloning works!")
        print("📁 Test audio saved: quick_test.wav")
        print("\n🎉 All systems working! You can now run your voice cloning script.")
    else:
        print("\n✅ XTTS model works!")
        print("⚠️ Add reference_voice.wav to test voice cloning")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print("\n🔧 Troubleshooting:")
    print("1. Check PyTorch version (should be 2.5.1 or lower)")
    print("2. Reinstall: pip uninstall torch torchcodec -y")
    print("3. Install stable: pip install torch==2.5.1 torchaudio==2.5.1")
    print("4. Reinstall TTS: pip install --upgrade TTS")