"""
XTTS v2 Voice Cloning - Enhanced Version
Works with PyTorch 2.6+ and handles torchcodec issues gracefully
"""

import torch
import torch.serialization
import warnings
import os
import sys

# Suppress torchcodec warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', module='torchcodec')

# Store original torch.load
_original_torch_load = torch.load

def patched_torch_load(*args, **kwargs):
    """Patched torch.load that sets weights_only=False for TTS models"""
    # Force weights_only=False for compatibility
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)

# Monkey patch torch.load
torch.load = patched_torch_load

print("✅ TTS patched to work with PyTorch 2.6+")
print(f"🔥 PyTorch version: {torch.__version__}")

# Import TTS after patching
from TTS.api import TTS

# Configuration
OUTPUT_DIR = "cloned_outputs"
REFERENCE_FILES = [
    "reference_voice_RE.wav",
    "my_voice.wav", 
    "speaker_sample.wav"
]

TEST_TEXTS = [
    "Hello! This is my cloned voice speaking.",
    "The voice cloning technology is working perfectly.",
    "I can now say anything in this cloned voice.",
    "This neural network has learned to mimic my speech patterns.",
    "Amazing how just a few minutes of audio can create this result!"
]

def check_pytorch_version():
    """Check if PyTorch version might have compatibility issues"""
    version = torch.__version__
    major, minor = version.split('.')[:2]
    
    if int(major) == 2 and int(minor) >= 9:
        print("⚠️  Warning: PyTorch 2.9+ detected")
        print("   TorchCodec may have compatibility issues")
        print("   If you see errors, downgrade to PyTorch 2.5.1:")
        print("   pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu")
        print()
    
    return True

def setup_output_directory():
    """Create output directory for cloned samples"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"📁 Output directory: {OUTPUT_DIR}/")

def find_reference_audio():
    """Find reference audio file"""
    for ref_file in REFERENCE_FILES:
        if os.path.exists(ref_file):
            size_kb = os.path.getsize(ref_file) / 1024
            duration = "unknown"
            
            # Try to get duration
            try:
                import librosa
                audio, sr = librosa.load(ref_file, sr=None, duration=1)
                duration_sec = librosa.get_duration(path=ref_file)
                duration = f"{duration_sec:.1f}s"
            except:
                pass
            
            print(f"🔍 Found reference audio: {ref_file}")
            print(f"   Size: {size_kb:.1f} KB, Duration: {duration}")
            return ref_file
    
    return None

def clone_voice_xtts(reference_audio_path, output_name="cloned_voice"):
    """
    Clone a voice using XTTS v2
    
    Args:
        reference_audio_path: Path to reference audio (30s-5min recommended)
        output_name: Base name for output files
    """
    
    print("\n🚀 Loading XTTS v2 for voice cloning...")
    
    try:
        # Load XTTS v2 model
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
        print("✅ XTTS v2 model loaded successfully")
    except Exception as e:
        print(f"❌ Error loading XTTS model: {e}")
        return False
    
    print(f"\n🎤 Cloning voice from: {reference_audio_path}")
    print(f"🎯 Generating {len(TEST_TEXTS)} samples...\n")
    
    successful = 0
    failed = 0
    
    for i, text in enumerate(TEST_TEXTS, 1):
        output_file = os.path.join(OUTPUT_DIR, f"{output_name}_sample_{i:02d}.wav")
        
        print(f"📝 Sample {i}/{len(TEST_TEXTS)}: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        try:
            # Clone the voice!
            tts.tts_to_file(
                text=text,
                file_path=output_file,
                speaker_wav=reference_audio_path,
                language="en",
                split_sentences=True  # Better quality for longer texts
            )
            print(f"   ✅ Saved: {output_file}")
            successful += 1
            
        except RuntimeError as e:
            # Handle torchcodec errors gracefully
            if "torchcodec" in str(e).lower() or "libtorchcodec" in str(e).lower():
                print(f"   ⚠️  TorchCodec warning (continuing...)")
                
                # Try without split_sentences
                try:
                    tts.tts_to_file(
                        text=text,
                        file_path=output_file,
                        speaker_wav=reference_audio_path,
                        language="en",
                        split_sentences=False
                    )
                    print(f"   ✅ Saved: {output_file} (without sentence splitting)")
                    successful += 1
                except Exception as e2:
                    print(f"   ❌ Failed: {str(e2)[:100]}")
                    failed += 1
            else:
                print(f"   ❌ Error: {str(e)[:100]}")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")
            failed += 1
    
    # Summary
    print("\n" + "="*60)
    print(f"🎵 Voice cloning complete!")
    print(f"✅ Successfully generated: {successful}/{len(TEST_TEXTS)} samples")
    
    if failed > 0:
        print(f"⚠️  Failed: {failed}/{len(TEST_TEXTS)} samples")
        print("\n💡 To fix errors:")
        print("   1. Downgrade PyTorch to 2.5.1:")
        print("      pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu")
        print("   2. Or run: python test_setup.py")
    
    if successful > 0:
        print(f"\n📁 Output location: {OUTPUT_DIR}/")
        print("\n🎧 Listen to your cloned voice samples!")
    
    print("="*60)
    
    return successful > 0

def prepare_reference_audio():
    """Create audio cleaning script"""
    
    prep_script = '''"""
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
    print(f"\\n💡 Use this file as reference_voice_RE.wav")

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
'''
    
    with open("clean_reference_audio.py", "w", encoding="utf-8") as f:
        f.write(prep_script)
    
    print("🧹 Audio cleaning script created: clean_reference_audio.py")
    print("   Usage: python clean_reference_audio.py your_audio.wav")

def show_instructions():
    """Show setup instructions"""
    print("\n" + "="*60)
    print("⚠️  No reference audio found!")
    print("="*60)
    print("\n📋 Place your reference audio as one of these names:")
    for ref_file in REFERENCE_FILES:
        print(f"   • {ref_file}")
    
    print("\n🎯 Recording tips for best results:")
    print("   ✓ Duration: 1-5 minutes (more is better)")
    print("   ✓ Environment: Quiet room, minimal background noise")
    print("   ✓ Content: Read naturally, vary your intonation")
    print("   ✓ Quality: Use a decent microphone if possible")
    print("   ✓ Format: WAV file, 16-bit, 22050Hz or 44100Hz")
    
    print("\n💡 Quick start:")
    print("   1. Record clear speech (1-5 minutes)")
    print("   2. Save as 'reference_voice_RE.wav' in this directory")
    print("   3. Run: python voice_cloning_xtts.py")
    
    print("\n🧹 To clean noisy audio:")
    print("   1. Save raw recording as 'my_recording.wav'")
    print("   2. Run: python clean_reference_audio.py my_recording.wav reference_voice_RE.wav")
    print("   3. Run: python voice_cloning_xtts.py")
    
    print("="*60)

def main():
    """Main execution"""
    
    print("🎭 XTTS v2 Voice Cloning Setup")
    print("="*60)
    
    # Check PyTorch version
    check_pytorch_version()
    
    # Setup output directory
    setup_output_directory()
    
    # Find reference audio
    reference_audio = find_reference_audio()
    
    if reference_audio:
        # Clone the voice!
        success = clone_voice_xtts(reference_audio, "my_cloned_voice")
        
        if not success:
            print("\n💡 If you're getting errors, try:")
            print("   python test_setup.py")
        
    else:
        # No reference audio found
        show_instructions()
        prepare_reference_audio()

if __name__ == "__main__":
    main()