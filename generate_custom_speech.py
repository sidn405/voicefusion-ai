from TTS.api import TTS

# Load XTTS
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)

# Your custom text
custom_text = """
Welcome to my channel! Today we're going to discuss 
artificial intelligence and voice cloning technology.
"""

# Generate with your cloned voice
tts.tts_to_file(
    text=custom_text,
    file_path="custom_speech.wav",
    speaker_wav="reference_voice.wav",  # Your reference
    language="en"
)

print("✅ Custom speech generated: custom_speech.wav")