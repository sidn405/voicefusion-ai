"""
Further Optimize Reference Audio
Take your good reference and make it even better
"""

import librosa
import soundfile as sf
import numpy as np

print("🔧 Further Optimizing Reference Audio")
print("="*70)

INPUT_FILE = "reference_voice.wav"
OUTPUT_FILE = "reference_voice_optimized.wav"

# Load
print(f"\n1️⃣ Loading {INPUT_FILE}...")
audio, sr = librosa.load(INPUT_FILE, sr=22050, mono=True)
original_duration = len(audio) / sr
original_max = np.max(np.abs(audio))

print(f"   Duration: {original_duration:.2f}s ({original_duration/60:.2f} min)")
print(f"   Sample rate: {sr} Hz")
print(f"   Current peak: {original_max:.3f} ({original_max*100:.1f}%)")

# Trim excessive silence
print(f"\n2️⃣ Trimming silence...")
audio_trimmed, _ = librosa.effects.trim(audio, top_db=20)
trimmed_duration = len(audio_trimmed) / sr
removed = original_duration - trimmed_duration

print(f"   Removed {removed:.2f}s of silence")
print(f"   New duration: {trimmed_duration:.2f}s ({trimmed_duration/60:.2f} min)")

# Amplify to optimal level (75-80%)
print(f"\n3️⃣ Optimizing volume...")
target_peak = 0.78  # 78% - ideal for XTTS
current_peak = np.max(np.abs(audio_trimmed))

if current_peak > 0:
    audio_amplified = audio_trimmed * (target_peak / current_peak)
    amplification = target_peak / current_peak
    print(f"   Amplified {amplification:.2f}x")
    print(f"   Peak: {current_peak:.3f} → {target_peak:.3f}")
else:
    audio_amplified = audio_trimmed
    print(f"   ⚠️  Audio is silent!")

# Enhance speech frequencies
print(f"\n4️⃣ Enhancing speech clarity...")
audio_enhanced = librosa.effects.preemphasis(audio_amplified, coef=0.97)

# Apply gentle compression (reduces dynamic range for more consistent volume)
print(f"\n5️⃣ Applying gentle compression...")

# Simple compression: reduce peaks, boost quiet parts
threshold = 0.6
ratio = 2.0

audio_compressed = np.copy(audio_enhanced)
loud_mask = np.abs(audio_compressed) > threshold

# Compress loud parts
audio_compressed[loud_mask] = np.sign(audio_compressed[loud_mask]) * (
    threshold + (np.abs(audio_compressed[loud_mask]) - threshold) / ratio
)

# Normalize after compression
audio_normalized = librosa.util.normalize(audio_compressed) * 0.78

# Final clipping safety
audio_final = np.clip(audio_normalized, -1.0, 1.0)

final_peak = np.max(np.abs(audio_final))
final_rms = np.sqrt(np.mean(audio_final**2))

print(f"   Final peak: {final_peak:.3f}")
print(f"   Final RMS: {final_rms:.3f}")

# Save
print(f"\n6️⃣ Saving optimized audio...")
sf.write(OUTPUT_FILE, audio_final, sr, subtype='PCM_16', format='WAV')

print(f"\n" + "="*70)
print(f"✅ OPTIMIZATION COMPLETE!")
print(f"="*70)

print(f"\n📊 Improvements:")
print(f"   Duration: {original_duration:.1f}s → {trimmed_duration:.1f}s")
print(f"   Peak level: {original_max*100:.1f}% → {final_peak*100:.1f}%")
print(f"   Clarity: Enhanced")
print(f"   Consistency: Improved")

print(f"\n📁 Files:")
print(f"   Original: {INPUT_FILE}")
print(f"   Optimized: {OUTPUT_FILE}")

print(f"\n🎯 Next Steps:")
print(f"   1. Test the optimized version:")
print(f"      python voice_cloning_xtts.py")
print(f"      (Make sure it uses {OUTPUT_FILE})")
print(f"   ")
print(f"   2. Compare quality:")
print(f"      Listen to samples from both versions")
print(f"   ")
print(f"   3. If better, replace original:")
print(f"      Move-Item {OUTPUT_FILE} {INPUT_FILE} -Force")

print(f"\n💡 The optimized version should give:")
print(f"   • More consistent volume")
print(f"   • Better speech clarity")
print(f"   • Cleaner voice characteristics")
print(f"   • Potentially better cloning quality")