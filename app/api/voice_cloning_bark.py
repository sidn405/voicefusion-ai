from TTS.api import TTS
import os

def clone_voice_bark(reference_audio_path):
    """Voice cloning with Bark model"""
    
    print("🐕 Loading Bark for voice cloning...")
    
    # Load Bark (supports voice cloning with very little data)
    tts = TTS("tts_models/multilingual/multi-dataset/bark", gpu=False)
    
    # Bark can clone voices from short samples
    test_texts = [
        "This is Bark neural voice cloning in action.",
        "I can speak with emotional expression and natural rhythm.",
        "The voice characteristics are preserved remarkably well."
    ]
    
    for i, text in enumerate(test_texts):
        output_file = f"bark_cloned_{i+1:02d}.wav"
        
        try:
            tts.tts_to_file(
                text=text,
                file_path=output_file,
                speaker_wav=reference_audio_path
            )
            print(f"✅ Generated: {output_file}")
            
        except Exception as e:
            print(f"❌ Bark error: {e}")
            print("💡 Trying without speaker reference...")
            
            # Fallback without cloning
            tts.tts_to_file(text=text, file_path=output_file)
    
    print("🎵 Bark voice cloning complete!")

if __name__ == "__main__":
    if os.path.exists("reference_voice.wav"):
        clone_voice_bark("reference_voice.wav")
    else:
        print("⚠️  Need reference_voice.wav for cloning!")