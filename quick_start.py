"""
Quick Start Script for LawBot 360 Voice Sales Agent
Run this first to test in text mode
"""

import os
import sys
import stripe

print("🤖 LawBot 360 Voice Sales Agent - Quick Start")
print("="*70)

# Check Python version
if sys.version_info < (3, 11):
    print("⚠️  Warning: Python 3.11+ recommended")

# Check for required packages
try:
    import openai
    print("✅ OpenAI installed")
except ImportError:
    print("❌ OpenAI not installed")
    print("   Run: pip install openai")
    sys.exit(1)

# Check for API key
if not os.getenv("OPENAI_API_KEY"):
    print("❌ OPENAI_API_KEY not set")
    print("\n📋 Setup steps:")
    print("1. Get API key: https://console.anthropic.com")
    print("2. Create .env file:")
    print("   echo 'OPENAI_API_KEY=your_key' > .env")
    print("3. Or export: export OPENAI_API_KEY=your_key")
    sys.exit(1)

print("✅ OPENAI_API_KEY set")

# Check for reference voice
if not os.path.exists("reference_voice.wav"):
    print("⚠️  reference_voice.wav not found")
    print("   Voice mode will not work without it")
    print("   But text mode works fine!")
else:
    print("✅ reference_voice.wav found")

print("\n" + "="*70)
print("🎯 Starting in TEXT MODE")
print("="*70)
print("\nThis lets you test the conversation without voice/phone.")
print("Type your responses as if you're on the call.\n")

input("Press ENTER to start...")

# Import and run
from lawbot_voice_sales_agent import VoiceSalesBot

bot = VoiceSalesBot()
bot.run_text_conversation()