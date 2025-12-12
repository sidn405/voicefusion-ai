"""
FIX: Voice Clone Sounds Completely Wrong
When XTTS generates a different voice entirely
"""

from TTS.api import TTS
import librosa
import soundfile as sf
import numpy as np
import os

print("🔧 FIXING: Voice clone doesn't match reference")
print("="*70)

# Step 1: Optimize reference audio
print("\n1️⃣ OPTIMIZING REFERENCE AUDIO")
print("-"*70)

input_file = "reference_voice.wav"

if not os.path.exists(input_file):
    print(f"❌ {input_file} not found!")
    exit(1)

# Load
print(f"Loading {input_file}...")
audio, sr = librosa.load(input_file, sr=22050, mono=True)
print(f"✅ Duration: {len(audio)/sr:.2f}s")

# Remove excessive silence
print("Trimming silence...")
audio_trimmed, _ = librosa.effects.trim(audio, top_db=20)

# IMPORTANT: Amplify to proper level
# Quiet audio can cause XTTS to default to generic voice!
print("Amplifying audio...")
target_peak = 0.8  # 80% of maximum
current_peak = np.max(np.abs(audio_trimmed))

if current_peak > 0:
    amplification_factor = target_peak / current_peak
    audio_amplified = audio_trimmed * amplification_factor
    print(f"✅ Amplified {amplification_factor:.2f}x (was {current_peak:.3f}, now {target_peak:.3f})")
else:
    print("⚠️  Audio is silent!")
    audio_amplified = audio_trimmed

# Apply speech enhancement
print("Enhancing speech frequencies...")
audio_enhanced = librosa.effects.preemphasis(audio_amplified, coef=0.97)

# Clip to valid range
audio_final = np.clip(audio_enhanced, -1.0, 1.0)

# Save optimized version
optimized_file = "reference_voice_FIXED.wav"
sf.write(optimized_file, audio_final, sr, subtype='PCM_16', format='WAV')

print(f"\n✅ Saved optimized audio: {optimized_file}")
print(f"   Duration: {len(audio_final)/sr:.2f}s")
print(f"   Peak level: {np.max(np.abs(audio_final)):.3f}")

# Step 2: Test with XTTS using explicit parameters
print("\n2️⃣ TESTING WITH XTTS (FORCED REFERENCE)")
print("-"*70)

print("Loading XTTS model...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)

# Test with very explicit reference loading
test_text = "Hello, this is a test. Can you hear my actual voice now? This should sound like me."

print("\nGenerating test with FIXED reference...")
print("(Using explicit parameters to force reference usage)")

try:
    # Method 1: Standard method with fixed audio
    tts.tts_to_file(
        text=test_text,
        file_path="test_FIXED_method1.wav",
        speaker_wav=optimized_file,  # Use optimized file
        language="en",
        split_sentences=True
    )
    print("✅ Method 1 complete: test_FIXED_method1.wav")
except Exception as e:
    print(f"⚠️  Method 1 failed: {e}")

try:
    # Method 2: Without sentence splitting
    tts.tts_to_file(
        text=test_text,
        file_path="test_FIXED_method2.wav",
        speaker_wav=optimized_file,
        language="en",
        split_sentences=False
    )
    print("✅ Method 2 complete: test_FIXED_method2.wav")
except Exception as e:
    print(f"⚠️  Method 2 failed: {e}")

# Step 3: Generate multiple samples for comparison
print("\n3️⃣ GENERATING COMPARISON SAMPLES")
print("-"*70)

test_texts = [
    "Hey, what's up? This is me speaking naturally.",
    "I want to hear if this actually sounds like my voice.",
    "The previous version sounded nothing like me, let's see if this is better.",
]

print("\nGenerating 3 test samples with fixed audio...")

for i, text in enumerate(test_texts, 1):
    output = f"fixed_sample_{i}.wav"
    
    try:
        tts.tts_to_file(
            text=text,
            file_path=output,
            speaker_wav=optimized_file,
            language="en",
            split_sentences=False  # Try without splitting
        )
        print(f"✅ Sample {i}: {output}")
    except Exception as e:
        print(f"❌ Sample {i} failed: {e}")

print("\n" + "="*70)
print("🎧 TESTING COMPLETE")
print("="*70)

print("\n📁 Generated files:")
print(f"   • {optimized_file} (optimized reference)")
print(f"   • test_FIXED_method1.wav")
print(f"   • test_FIXED_method2.wav")
print(f"   • fixed_sample_1.wav")
print(f"   • fixed_sample_2.wav")
print(f"   • fixed_sample_3.wav")

print("\n🎯 LISTEN TO THESE FILES:")
print("   1. Do they sound more like you now?")
print("   2. Compare to test_1_default.wav")
print("   3. If better → use reference_voice_FIXED.wav going forward")
print("   4. If still wrong → reference audio quality issue, need to re-record")

print("\n💡 If this STILL doesn't work:")
print("   Your reference audio may have:")
print("   • Too much background noise")
print("   • Audio quality too poor")
print("   • Recording issues")
print("   → SOLUTION: Record fresh audio in quiet room with good mic")
print("   → Duration: 5-10 minutes of natural speech")

print("\n✅ To use the fixed reference:")
print("   Move-Item reference_voice_FIXED.wav reference_voice.wav -Force")
print("   python voice_cloning_xtts.py")