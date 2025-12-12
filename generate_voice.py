"""
Optimized Voice Cloning Generator
Generate high-quality voice clones with your reference
"""

from TTS.api import TTS
import os
from datetime import datetime

print("🎤 Optimized Voice Cloning Generator")
print("="*70)

# Load model
print("Loading XTTS v2...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
print("✅ Model loaded")

# Configuration
REFERENCE_AUDIO = "reference_voice.wav"
OUTPUT_DIR = "generated_speech"
LANGUAGE = "en"

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_speech(text, filename=None, split_sentences=True):
    """Generate speech with optimized settings"""
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"speech_{timestamp}.wav"
    
    output_path = os.path.join(OUTPUT_DIR, filename)
    
    try:
        tts.tts_to_file(
            text=text,
            file_path=output_path,
            speaker_wav=REFERENCE_AUDIO,
            language=LANGUAGE,
            split_sentences=split_sentences
        )
        return output_path
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def interactive_mode():
    """Interactive text-to-speech generation"""
    
    print("\n🎙️  Interactive Voice Generation")
    print("="*70)
    print("Type your text and press Enter to generate speech")
    print("Commands:")
    print("  'quit' or 'exit' - Exit program")
    print("  'batch' - Switch to batch mode")
    print("="*70)
    
    count = 1
    while True:
        print(f"\n[{count}] Enter text (or command):")
        text = input("> ").strip()
        
        if not text:
            continue
        
        if text.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        
        if text.lower() == 'batch':
            batch_mode()
            break
        
        print(f"🔄 Generating...")
        output = generate_speech(text, f"interactive_{count:03d}.wav")
        
        if output:
            print(f"✅ Generated: {output}")
            count += 1
        else:
            print("❌ Generation failed")

def batch_mode():
    """Batch generate multiple texts"""
    
    print("\n📦 Batch Generation Mode")
    print("="*70)
    print("Enter multiple texts (one per line)")
    print("Type 'DONE' when finished")
    print("="*70)
    
    texts = []
    line_num = 1
    
    while True:
        text = input(f"[{line_num}] ").strip()
        
        if text.upper() == 'DONE':
            break
        
        if text:
            texts.append(text)
            line_num += 1
    
    if not texts:
        print("❌ No texts entered")
        return
    
    print(f"\n🔄 Generating {len(texts)} audio files...")
    
    for i, text in enumerate(texts, 1):
        print(f"\n[{i}/{len(texts)}] Generating...")
        print(f"   Text: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        output = generate_speech(text, f"batch_{i:03d}.wav")
        
        if output:
            print(f"   ✅ Saved: {output}")
        else:
            print(f"   ❌ Failed")
    
    print(f"\n✅ Batch complete! Generated {len(texts)} files")
    print(f"📁 Location: {OUTPUT_DIR}/")

def preset_samples():
    """Generate preset sample phrases"""
    
    print("\n🎯 Generating Preset Samples")
    print("="*70)
    
    samples = {
        "greeting": "Hey! How's it going? Good to hear from you.",
        "introduction": "Hi, my name is [Your Name], and I'm excited to share this with you today.",
        "question": "Have you ever wondered what it would be like to clone your own voice?",
        "excited": "This is absolutely incredible! I can't believe how well this works!",
        "serious": "Let me explain this clearly. The technology behind voice cloning is fascinating.",
        "casual": "So yeah, that's pretty much how it went down. What do you think?",
        "professional": "Thank you for your time. I look forward to discussing this further.",
        "storytelling": "Let me tell you about something interesting that happened yesterday.",
    }
    
    print(f"Generating {len(samples)} preset samples...")
    
    for name, text in samples.items():
        print(f"\n🔄 {name.capitalize()}...")
        print(f"   \"{text[:60]}...\"")
        
        output = generate_speech(text, f"preset_{name}.wav")
        
        if output:
            print(f"   ✅ Generated")
        else:
            print(f"   ❌ Failed")
    
    print(f"\n✅ Presets complete!")
    print(f"📁 Location: {OUTPUT_DIR}/")

def generate_from_file(filepath):
    """Generate speech from text file"""
    
    print(f"\n📄 Generating from file: {filepath}")
    print("="*70)
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        print("❌ File is empty")
        return
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    print(f"Found {len(paragraphs)} paragraph(s)")
    
    for i, para in enumerate(paragraphs, 1):
        print(f"\n[{i}/{len(paragraphs)}] Generating...")
        print(f"   Length: {len(para)} characters")
        
        output = generate_speech(para, f"from_file_{i:03d}.wav")
        
        if output:
            print(f"   ✅ Generated")
        else:
            print(f"   ❌ Failed")
    
    print(f"\n✅ File processing complete!")
    print(f"📁 Location: {OUTPUT_DIR}/")

def main_menu():
    """Main menu"""
    
    print("\n🎙️  Choose a mode:")
    print("="*70)
    print("1. Interactive Mode - Enter text line by line")
    print("2. Batch Mode - Enter multiple texts at once")
    print("3. Preset Samples - Generate sample phrases")
    print("4. From File - Generate from text file")
    print("5. Custom Single - Generate one custom text")
    print("6. Exit")
    print("="*70)
    
    choice = input("\nSelect option (1-6): ").strip()
    
    if choice == '1':
        interactive_mode()
    elif choice == '2':
        batch_mode()
    elif choice == '3':
        preset_samples()
    elif choice == '4':
        filepath = input("Enter text file path: ").strip()
        generate_from_file(filepath)
    elif choice == '5':
        text = input("Enter your text: ").strip()
        if text:
            output = generate_speech(text, "custom_single.wav")
            if output:
                print(f"✅ Generated: {output}")
    elif choice == '6':
        print("👋 Goodbye!")
        return
    else:
        print("❌ Invalid choice")
        main_menu()

if __name__ == "__main__":
    
    # Check if reference exists
    if not os.path.exists(REFERENCE_AUDIO):
        print(f"❌ Reference audio not found: {REFERENCE_AUDIO}")
        print("   Please ensure reference_voice.wav exists in this directory")
        exit(1)
    
    print(f"✅ Reference audio: {REFERENCE_AUDIO}")
    print(f"📁 Output directory: {OUTPUT_DIR}/")
    
    main_menu()