"""
Voice Clone Quality Comparison Tool
Generate multiple versions with different settings to find best quality
"""

from TTS.api import TTS
import os

print("🎤 Voice Clone Quality Comparison Tool")
print("="*70)

# Load model once
print("Loading XTTS v2...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)

# Test text - use YOUR typical speaking style
test_texts = [
    # Conversational
    "Hey, how are you doing today? I wanted to talk about something interesting.",
    
    # Expressive
    "This is absolutely amazing! I can't believe how well this technology works!",
    
    # Serious
    "Let me explain this carefully. The process involves several important steps.",
    
    # Question
    "Have you ever wondered how voice cloning actually works? It's fascinating!",
]

# Create output directory
os.makedirs("quality_tests", exist_ok=True)

print("\nGenerating comparison samples...")
print("Testing different settings...")

for i, text in enumerate(test_texts, 1):
    print(f"\n{i}. Testing: \"{text[:50]}...\"")
    
    # Version A: Default settings
    output_a = f"quality_tests/test_{i}_default.wav"
    tts.tts_to_file(
        text=text,
        file_path=output_a,
        speaker_wav="reference_voice.wav",
        language="en",
        split_sentences=True
    )
    print(f"   ✅ Default: {output_a}")
    
    # Version B: Without sentence splitting
    output_b = f"quality_tests/test_{i}_no_split.wav"
    tts.tts_to_file(
        text=text,
        file_path=output_b,
        speaker_wav="reference_voice.wav",
        language="en",
        split_sentences=False
    )
    print(f"   ✅ No split: {output_b}")

print("\n" + "="*70)
print("✅ Comparison tests complete!")
print(f"📁 Location: quality_tests/")
print("\n🎧 Listen to each version:")
print("   1. Compare test_1_default.wav vs test_1_no_split.wav")
print("   2. Which sounds more like you?")
print("   3. Use those settings for your final voice cloning")
print("\n💡 Tips:")
print("   • Play on good speakers/headphones")
print("   • Compare to your actual voice recording")
print("   • Check: tone, pitch, accent, naturalness")
print("="*70)

# Open folder
import subprocess
try:
    subprocess.run(["explorer", "quality_tests"], check=False)
except:
    print("\n📁 Open folder manually: quality_tests/")