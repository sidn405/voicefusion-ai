"""
Voice Cloning Diagnostic & Fix
Identifies why voice cloning isn't capturing your voice
"""

import os
import sys

def diagnose_reference_audio(filepath="reference_voice.wav"):
    """Diagnose issues with reference audio"""
    
    print("🔍 DIAGNOSING REFERENCE AUDIO")
    print("="*70)
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    import librosa
    import soundfile as sf
    import numpy as np
    
    # Load audio
    print(f"\n1️⃣ Loading: {filepath}")
    audio, sr = librosa.load(filepath, sr=22050, mono=True)
    duration = len(audio) / sr
    
    print(f"   Duration: {duration:.2f}s ({duration/60:.2f} minutes)")
    print(f"   Sample rate: {sr} Hz")
    print(f"   Samples: {len(audio)}")
    
    # Check volume
    print(f"\n2️⃣ Checking audio levels...")
    rms = np.sqrt(np.mean(audio**2))
    max_amplitude = np.max(np.abs(audio))
    
    print(f"   RMS level: {rms:.4f}")
    print(f"   Max amplitude: {max_amplitude:.4f}")
    
    issues = []
    
    if rms < 0.05:
        print(f"   ⚠️  Audio is quiet (RMS: {rms:.4f})")
        issues.append("quiet")
    else:
        print(f"   ✅ Volume is okay")
    
    # Check for speech content
    print(f"\n3️⃣ Analyzing speech content...")
    
    # Trim silence
    audio_trimmed, _ = librosa.effects.trim(audio, top_db=20)
    trimmed_duration = len(audio_trimmed) / sr
    silence_removed = duration - trimmed_duration
    
    print(f"   Original: {duration:.2f}s")
    print(f"   After trim: {trimmed_duration:.2f}s")
    print(f"   Silence: {silence_removed:.2f}s ({silence_removed/duration*100:.1f}%)")
    
    if silence_removed > duration * 0.5:
        print(f"   ⚠️  More than 50% is silence!")
        issues.append("silence")
    
    # Check frequency content (voice should be 100-4000 Hz)
    print(f"\n4️⃣ Checking frequency content...")
    
    # Get spectral centroid (indicates where most energy is)
    spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
    avg_centroid = np.mean(spectral_centroids)
    
    print(f"   Spectral centroid: {avg_centroid:.1f} Hz")
    
    if avg_centroid < 200 or avg_centroid > 3000:
        print(f"   ⚠️  Frequency content unusual for speech")
        issues.append("frequency")
    else:
        print(f"   ✅ Frequency range good for speech")
    
    # Summary
    print(f"\n" + "="*70)
    print(f"📊 DIAGNOSIS SUMMARY")
    print("="*70)
    
    if not issues:
        print("✅ Audio quality appears good!")
        print("   Issue might be with XTTS processing, not audio file")
    else:
        print(f"⚠️  Found {len(issues)} issue(s):")
        for issue in issues:
            if issue == "quiet":
                print("   • Audio is too quiet - needs amplification")
            elif issue == "silence":
                print("   • Too much silence - needs trimming")
            elif issue == "frequency":
                print("   • Unusual frequency content - check recording")
    
    return issues

def fix_reference_audio(input_path="reference_voice.wav", output_path="reference_voice_optimized.wav"):
    """Fix common issues with reference audio"""
    
    print("\n🔧 FIXING REFERENCE AUDIO")
    print("="*70)
    
    import librosa
    import soundfile as sf
    import numpy as np
    
    # Load
    print("1️⃣ Loading audio...")
    audio, sr = librosa.load(input_path, sr=22050, mono=True)
    original_duration = len(audio) / sr
    print(f"   Loaded: {original_duration:.2f}s")
    
    # Remove silence
    print("\n2️⃣ Trimming silence...")
    audio_trimmed, _ = librosa.effects.trim(audio, top_db=20)
    print(f"   Removed {(len(audio) - len(audio_trimmed)) / sr:.2f}s of silence")
    
    # Normalize to proper level (target -3dB)
    print("\n3️⃣ Normalizing volume...")
    target_level = 0.7  # About -3dB
    current_max = np.max(np.abs(audio_trimmed))
    
    if current_max > 0:
        audio_normalized = audio_trimmed * (target_level / current_max)
        print(f"   Amplified from {current_max:.3f} to {target_level:.3f}")
    else:
        audio_normalized = audio_trimmed
        print(f"   ⚠️  Audio is silent!")
    
    # Apply preemphasis (enhances higher frequencies for speech clarity)
    print("\n4️⃣ Enhancing speech clarity...")
    audio_enhanced = librosa.effects.preemphasis(audio_normalized, coef=0.97)
    
    # Ensure it's in proper range
    audio_final = np.clip(audio_enhanced, -1.0, 1.0)
    
    # Save
    print("\n5️⃣ Saving optimized audio...")
    sf.write(
        output_path,
        audio_final,
        sr,
        subtype='PCM_16',
        format='WAV'
    )
    
    final_duration = len(audio_final) / sr
    
    print(f"\n✅ OPTIMIZATION COMPLETE!")
    print("="*70)
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Duration: {original_duration:.2f}s → {final_duration:.2f}s")
    print(f"Format: WAV, 16-bit PCM, {sr} Hz, Mono")
    print("\n💡 Use this file for voice cloning:")
    print(f"   Move-Item {output_path} reference_voice.wav -Force")
    print(f"   python voice_cloning_xtts.py")

def test_xtts_reference_loading():
    """Test if XTTS is actually using the reference audio"""
    
    print("\n🧪 TESTING XTTS REFERENCE LOADING")
    print("="*70)
    
    from TTS.api import TTS
    
    print("Loading XTTS model...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    
    test_text = "This is a test to verify the voice cloning is working correctly."
    
    # Test 1: Generate without reference (should be generic)
    print("\n1️⃣ Generating WITHOUT reference (generic voice)...")
    try:
        tts.tts_to_file(
            text=test_text,
            file_path="test_no_reference.wav",
            language="en"
        )
        print("   ✅ Generic voice saved: test_no_reference.wav")
    except:
        print("   ⚠️  No reference test failed")
    
    # Test 2: Generate WITH reference
    print("\n2️⃣ Generating WITH reference (should be YOUR voice)...")
    tts.tts_to_file(
        text=test_text,
        file_path="test_with_reference.wav",
        speaker_wav="reference_voice.wav",
        language="en"
    )
    print("   ✅ Cloned voice saved: test_with_reference.wav")
    
    print("\n🎧 COMPARE THESE FILES:")
    print("   • test_no_reference.wav (generic voice)")
    print("   • test_with_reference.wav (should be YOUR voice)")
    print("\n   If they sound the same, XTTS isn't using your reference properly!")

if __name__ == "__main__":
    print("🎤 VOICE CLONING DIAGNOSTIC TOOL")
    print("="*70)
    
    # Check if reference exists
    if not os.path.exists("reference_voice.wav"):
        print("❌ reference_voice.wav not found!")
        sys.exit(1)
    
    # Step 1: Diagnose
    issues = diagnose_reference_audio("reference_voice.wav")
    
    # Step 2: Fix if needed
    if issues or input("\nWould you like to optimize the audio anyway? [y/N]: ").lower() == 'y':
        fix_reference_audio("reference_voice.wav", "reference_voice_optimized.wav")
        
        print("\n" + "="*70)
        print("🎯 NEXT STEPS:")
        print("="*70)
        print("1. Replace reference with optimized version:")
        print("   Move-Item reference_voice_optimized.wav reference_voice.wav -Force")
        print("\n2. Test XTTS reference loading:")
        print("   python diagnostic.py --test")
        print("\n3. Generate new voice samples:")
        print("   python voice_cloning_xtts.py")
    
    # Step 3: Test XTTS if requested
    if "--test" in sys.argv:
        test_xtts_reference_loading()