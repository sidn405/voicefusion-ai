"""
Simple Audio Recorder for Voice Cloning
Records properly formatted WAV files for XTTS
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime
import sys

def list_devices():
    """List available audio input devices"""
    print("\n🎤 Available input devices:")
    print("="*60)
    
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"  [{i}] {device['name']}")
            print(f"      Channels: {device['max_input_channels']}, Sample Rate: {device['default_samplerate']} Hz")
    
    print("="*60)

def record_audio(duration=60, output_file="reference_voice.wav", device=None):
    """
    Record audio for voice cloning
    
    Args:
        duration: Recording duration in seconds (default: 60)
        output_file: Output filename (default: reference_voice.wav)
        device: Input device ID (None = default)
    """
    
    sample_rate = 22050  # Optimal for XTTS
    channels = 1  # Mono
    
    print("\n🎙️  Voice Recording for Cloning")
    print("="*60)
    print(f"Duration: {duration} seconds")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Output: {output_file}")
    print("="*60)
    
    print("\n📋 Recording tips:")
    print("  • Speak naturally and clearly")
    print("  • Vary your intonation and emotion")
    print("  • Read from a book, article, or script")
    print("  • Minimize background noise")
    print("  • Stay consistent distance from mic")
    
    input("\n🎬 Press ENTER to start recording...")
    
    print(f"\n🔴 RECORDING... ({duration} seconds)")
    print("   Speak now! Read naturally and vary your tone.")
    
    try:
        # Record audio
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            dtype='float32',
            device=device
        )
        
        sd.wait()  # Wait until recording is finished
        
        print("✅ Recording complete!")
        
        # Process audio
        print("\n🔄 Processing audio...")
        
        # Normalize
        recording = recording / np.max(np.abs(recording))
        
        # Save as WAV
        sf.write(
            output_file,
            recording,
            sample_rate,
            subtype='PCM_16',
            format='WAV'
        )
        
        file_size = len(recording) / sample_rate
        print(f"✅ Saved: {output_file}")
        print(f"   Duration: {file_size:.2f} seconds")
        print(f"   Format: WAV, 16-bit PCM, {sample_rate} Hz, Mono")
        
        print(f"\n🎯 Next step:")
        print(f"   python voice_cloning_xtts_improved.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Recording failed: {e}")
        return False

def main():
    """Main execution"""
    
    print("🎙️  Voice Cloning Audio Recorder")
    print("="*60)
    
    # Parse arguments
    duration = 60  # Default 60 seconds
    output_file = "reference_voice.wav"
    device = None
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_devices()
            return
        
        try:
            duration = int(sys.argv[1])
        except:
            print(f"❌ Invalid duration: {sys.argv[1]}")
            print("   Usage: python record_voice.py [duration_seconds] [output_file.wav] [device_id]")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    if len(sys.argv) > 3:
        try:
            device = int(sys.argv[3])
        except:
            print(f"❌ Invalid device ID: {sys.argv[3]}")
            sys.exit(1)
    
    # Show usage if no args
    if len(sys.argv) == 1:
        print("\nUsage:")
        print("  List devices:    python record_voice.py list")
        print("  Quick record:    python record_voice.py")
        print("  Custom duration: python record_voice.py 120 my_voice.wav")
        print("  Choose device:   python record_voice.py 60 voice.wav 0")
        print("\nRecommended: 60-180 seconds (1-3 minutes)")
        print()
        
        choice = input("Record with defaults (60 seconds)? [Y/n]: ").strip().lower()
        if choice and choice != 'y':
            print("Cancelled.")
            return
    
    # Record
    record_audio(duration, output_file, device)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Recording cancelled by user")
        sys.exit(0)