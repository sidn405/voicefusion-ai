"""
Audio Format Checker & Converter
Fixes WAV files that aren't recognized by TTS/soundfile
"""

import os
import sys

def check_audio_file(filepath):
    """Check audio file format and show details"""
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    file_size = os.path.getsize(filepath) / 1024  # KB
    print(f"\n📁 File: {filepath}")
    print(f"   Size: {file_size:.1f} KB")
    
    # Try different libraries to read the file
    print("\n🔍 Testing file format...")
    
    # Test 1: soundfile (what TTS uses)
    try:
        import soundfile as sf
        with sf.SoundFile(filepath) as f:
            print(f"✅ soundfile: Can read")
            print(f"   Sample rate: {f.samplerate} Hz")
            print(f"   Channels: {f.channels}")
            print(f"   Duration: {len(f) / f.samplerate:.2f} seconds")
            print(f"   Format: {f.format}")
            print(f"   Subtype: {f.subtype}")
            return True
    except Exception as e:
        print(f"❌ soundfile: Cannot read - {str(e)}")
    
    # Test 2: librosa
    try:
        import librosa
        y, sr = librosa.load(filepath, sr=None, duration=1)
        print(f"✅ librosa: Can read")
        print(f"   Sample rate: {sr} Hz")
        full_duration = librosa.get_duration(path=filepath)
        print(f"   Duration: {full_duration:.2f} seconds")
    except Exception as e:
        print(f"❌ librosa: Cannot read - {str(e)}")
    
    # Test 3: wave (standard library)
    try:
        import wave
        with wave.open(filepath, 'rb') as w:
            print(f"✅ wave: Can read")
            print(f"   Sample rate: {w.getframerate()} Hz")
            print(f"   Channels: {w.getnchannels()}")
            print(f"   Duration: {w.getnframes() / w.getframerate():.2f} seconds")
            print(f"   Sample width: {w.getsampwidth()} bytes")
    except Exception as e:
        print(f"❌ wave: Cannot read - {str(e)}")
    
    return False

def convert_to_proper_wav(input_path, output_path="reference_voice_fixed.wav"):
    """Convert audio to proper WAV format for TTS"""
    
    print(f"\n🔄 Converting: {input_path}")
    print(f"   Output: {output_path}")
    
    try:
        import librosa
        import soundfile as sf
        
        # Load audio with librosa (handles many formats)
        print("   Loading audio...")
        audio, sr = librosa.load(input_path, sr=22050, mono=True)
        
        duration = len(audio) / sr
        print(f"   Loaded: {duration:.2f} seconds @ {sr} Hz")
        
        # Trim silence
        print("   Trimming silence...")
        audio_trimmed, _ = librosa.effects.trim(audio, top_db=20)
        
        # Normalize
        print("   Normalizing volume...")
        audio_normalized = librosa.util.normalize(audio_trimmed)
        
        # Save as proper WAV file
        print("   Saving...")
        sf.write(
            output_path, 
            audio_normalized, 
            sr,
            subtype='PCM_16',  # 16-bit PCM (standard WAV)
            format='WAV'
        )
        
        final_duration = len(audio_normalized) / sr
        print(f"\n✅ Conversion successful!")
        print(f"   Output: {output_path}")
        print(f"   Duration: {final_duration:.2f} seconds")
        print(f"   Format: WAV, 16-bit PCM, {sr} Hz, Mono")
        print(f"\n💡 Use this file for voice cloning!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Conversion failed: {e}")
        return False

def create_test_wav():
    """Create a test WAV file if no reference audio exists"""
    
    print("\n🎵 Creating test WAV file...")
    
    try:
        import numpy as np
        import soundfile as sf
        
        # Generate 3 seconds of test audio (sine wave)
        sr = 22050
        duration = 3.0
        frequency = 440  # A4 note
        
        t = np.linspace(0, duration, int(sr * duration))
        audio = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        output_path = "test_audio.wav"
        sf.write(output_path, audio, sr, subtype='PCM_16', format='WAV')
        
        print(f"✅ Test file created: {output_path}")
        print(f"   This is just a test tone - you need real voice recording!")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test file: {e}")
        return False

def main():
    """Main execution"""
    
    print("🎵 Audio Format Checker & Converter")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  Check file:   python fix_audio_format.py check reference_voice.wav")
        print("  Convert file: python fix_audio_format.py convert input.wav output.wav")
        print("  Create test:  python fix_audio_format.py test")
        print("\nQuick fix:")
        print("  python fix_audio_format.py convert reference_voice.wav reference_voice_fixed.wav")
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == "check":
        if len(sys.argv) < 3:
            print("❌ Please specify file to check")
            print("   Usage: python fix_audio_format.py check reference_voice.wav")
            sys.exit(1)
        
        filepath = sys.argv[2]
        check_audio_file(filepath)
    
    elif command == "convert":
        if len(sys.argv) < 3:
            print("❌ Please specify input file")
            print("   Usage: python fix_audio_format.py convert input.wav [output.wav]")
            sys.exit(1)
        
        input_file = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else "reference_voice_fixed.wav"
        
        if not os.path.exists(input_file):
            print(f"❌ File not found: {input_file}")
            sys.exit(1)
        
        if convert_to_proper_wav(input_file, output_file):
            print(f"\n✅ Done! Now run:")
            print(f"   python voice_cloning_xtts_improved.py")
    
    elif command == "test":
        create_test_wav()
        print("\n⚠️  test_audio.wav is just a sine wave!")
        print("   You need to record actual speech for voice cloning.")
    
    else:
        print(f"❌ Unknown command: {command}")
        print("   Use: check, convert, or test")

if __name__ == "__main__":
    main()