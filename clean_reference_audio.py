"""
Audio Cleaning Script for Voice Cloning
Improves reference audio quality for better cloning results
"""

import librosa
import soundfile as sf
import numpy as np

def clean_audio_for_cloning(input_path, output_path="reference_voice_RE_clean.wav"):
    """
    Clean and prepare audio for voice cloning
    
    Args:
        input_path: Path to raw audio file
        output_path: Path to save cleaned audio
    """
    
    print(f"🔄 Processing: {input_path}")
    
    # Load audio
    audio, sr = librosa.load(input_path, sr=22050, mono=True)
    print(f"   Original: {len(audio)/sr:.2f}s @ {sr}Hz")
    
    # Remove silence from beginning and end
    audio_trimmed, _ = librosa.effects.trim(audio, top_db=20)
    print(f"   After trimming: {len(audio_trimmed)/sr:.2f}s")
    
    # Normalize volume
    audio_normalized = librosa.util.normalize(audio_trimmed)
    
    # Reduce noise (simple highpass filter)
    audio_filtered = librosa.effects.preemphasis(audio_normalized)
    
    # Save cleaned audio
    sf.write(output_path, audio_filtered, sr)
    
    print(f"✅ Cleaned audio saved: {output_path}")
    print(f"   Duration: {len(audio_filtered)/sr:.2f}s")
    print(f"   Sample rate: {sr}Hz")
    print(f"\n💡 Use this file as reference_voice_RE.wav")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python clean_reference_audio.py input.wav [output.wav]")
        print("Example: python clean_reference_audio.py my_recording.wav reference_voice_RE.wav")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "reference_voice_RE_clean.wav"
    
    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        sys.exit(1)
    
    clean_audio_for_cloning(input_file, output_file)
