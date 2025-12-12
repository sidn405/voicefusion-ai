import urllib.request
import os
from TTS.api import TTS

def download_demo_audio():
    """Download sample audio for testing"""
    
    # Create a simple demo audio using TTS
    print("🎤 Creating demo reference audio...")
    
    # Generate reference audio
    demo_tts = TTS("tts_models/en/ljspeech/vits", gpu=False)
    
    reference_text = """
    Hello, my name is Alex and this is my voice. 
    I speak clearly and naturally. 
    This audio will be used as a reference for voice cloning.
    The neural network will learn my speech patterns from this sample.
    """
    
    demo_tts.tts_to_file(
        text=reference_text,
        file_path="demo_reference_voice.wav"
    )
    
    print("✅ Demo reference audio created: demo_reference_voice.wav")
    return "demo_reference_voice.wav"

def clone_demo_voice():
    """Clone the demo voice"""
    
    print("🚀 Starting voice cloning demo...")
    
    # Create reference if it doesn't exist
    if not os.path.exists("demo_reference_voice.wav"):
        reference_file = download_demo_audio()
    else:
        reference_file = "demo_reference_voice.wav"
    
    # Load XTTS for cloning
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    
    # Clone with different text
    clone_texts = [
        "This is amazing! The voice cloning technology works perfectly.",
        "I can now say completely different words with the same voice.",
        "The neural network has successfully learned my vocal characteristics.",
        "Voice cloning opens up incredible possibilities for content creation."
    ]
    
    print(f"🎯 Cloning voice using: {reference_file}")
    
    for i, text in enumerate(clone_texts):
        output_file = f"cloned_demo_{i+1:02d}.wav"
        
        tts.tts_to_file(
            text=text,
            file_path=output_file,
            speaker_wav=reference_file,
            language="en"
        )
        
        print(f"   ✅ {output_file}")
    
    print("\n🎭 Voice cloning demo complete!")
    print("🌐 Compare original vs cloned at: http://35.226.41.158:8080")
    print("📊 Notice how the cloned voice maintains the same characteristics!")

if __name__ == "__main__":
    clone_demo_voice()

