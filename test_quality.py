from TTS.api import TTS

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)

# Test with YOUR voice describing something specific
test_text = """
Hey, this is a test of my voice cloning quality.
I'm really excited about this technology!
Can you hear how I naturally speak?
Let me tell you, it's pretty amazing.
"""

# Generate test
tts.tts_to_file(
    text=test_text,
    file_path="quality_test.wav",
    speaker_wav="reference_voice.wav",
    language="en",
    split_sentences=True  # Try False if this doesn't sound good
)

print("✅ Test generated: quality_test.wav")
print("   Listen and compare to your actual voice")