"""
LawBot 360 Voice Sales Agent - FastAPI Backend with Real-Time Voice Cloning
Handles Twilio webhooks with dynamic AI conversation using your cloned voice
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from twilio.twiml.voice_response import VoiceResponse, Dial, Gather
from twilio.rest import Client
import os
import resend
from openai import OpenAI
import uuid
from pathlib import Path

# Initialize FastAPI
app = FastAPI(title="LawBot 360 Voice Sales Agent")

# Create audio directory for generated files
AUDIO_DIR = Path("/tmp/audio")
AUDIO_DIR.mkdir(exist_ok=True)

# Initialize clients at module level (safe - no scipy yet)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
resend.api_key = os.getenv("RESEND_API_KEY")

twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

# Configuration
HUMAN_PHONE = os.getenv("PHONE")
REFERENCE_VOICE = "reference_voice.wav"
SERVER_URL = os.getenv("SERVER_URL", "https://voicefusion-ai-production.up.railway.app")

# TTS will be loaded lazily in routes
tts_instance = None

# Conversation memory (in production, use Redis/database)
conversations = {}


def get_tts():
    """Lazy load TTS - only when needed"""
    global tts_instance
    if tts_instance is None:
        print("🎤 Loading voice clone...")
        from TTS.api import TTS
        tts_instance = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
        print("✅ Voice clone loaded!")
    return tts_instance


def generate_speech(text: str) -> str:
    """Generate speech with cloned voice and return URL"""
    tts = get_tts()
    
    # Generate unique filename
    audio_id = str(uuid.uuid4())
    output_file = AUDIO_DIR / f"{audio_id}.wav"
    
    print(f"🎙️ Generating speech: '{text[:50]}...'")
    
    tts.tts_to_file(
        text=text,
        file_path=str(output_file),
        speaker_wav=REFERENCE_VOICE,
        language="en"
    )
    
    # Return public URL for Twilio to play
    audio_url = f"{SERVER_URL}/audio/{audio_id}.wav"
    print(f"✅ Audio ready: {audio_url}")
    
    return audio_url


def get_ai_response(call_sid: str, user_input: str, stage: str) -> str:
    """Get AI response based on conversation context"""
    
    # Initialize conversation if needed
    if call_sid not in conversations:
        conversations[call_sid] = {
            "history": [],
            "stage": "greeting",
            "client_name": None,
            "pain_points": []
        }
    
    conv = conversations[call_sid]
    conv["history"].append({"role": "user", "content": user_input})
    
    # Build system prompt based on stage
    system_prompt = f"""You are a sales expert for 4D Gaming, selling LawBot 360 ($25,000 AI client intake system).

Current stage: {stage}
Client name: {conv.get('client_name', 'Unknown')}

CRITICAL RULES:
1. Keep responses VERY SHORT (1-2 sentences max) - this is a phone call
2. Sound natural and conversational - like a real person calling
3. Listen to what they say and respond personally
4. Move the conversation toward closing the sale
5. If they want human, acknowledge and we'll transfer
6. Use their name when you know it
7. Be confident but not pushy - you're selling a $25k solution

PRICING: $25,000 one-time, $7,500 down payment to start

Your goal: Have a natural conversation that leads to a sale or human handoff.
"""
    
    # Get AI response
    messages = [
        {"role": "system", "content": system_prompt}
    ] + conv["history"][-10:]  # Last 10 messages
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            temperature=0.7,
            max_tokens=100  # Keep it short!
        )
        
        ai_response = response.choices[0].message.content
        conv["history"].append({"role": "assistant", "content": ai_response})
        
        return ai_response
        
    except Exception as e:
        print(f"❌ OpenAI error: {e}")
        return "I apologize, let me connect you with a human specialist who can help."


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "LawBot 360 Voice Sales Agent - Real-Time Voice Cloning",
        "voice_cloning": "enabled",
        "human_phone": HUMAN_PHONE
    }


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated audio files to Twilio"""
    audio_file = AUDIO_DIR / filename
    if audio_file.exists():
        return FileResponse(audio_file, media_type="audio/wav")
    return {"error": "Audio file not found"}


@app.post("/voice/incoming")
async def handle_incoming_call(request: Request):
    """Handle incoming calls with YOUR cloned voice"""
    
    form_data = await request.form()
    from_number = form_data.get('From')
    call_sid = form_data.get('CallSid')
    
    print(f"📞 Incoming call from {from_number}")
    
    response = VoiceResponse()
    
    # Generate greeting with YOUR voice
    greeting_text = ("Hi! This is an AI sales assistant calling from 4D Gaming about LawBot 360, "
                    "our AI-powered client intake system for law firms. "
                    "Press 1 to speak with me, or press 2 to transfer to a human immediately.")
    
    greeting_url = generate_speech(greeting_text)
    response.play(greeting_url)
    
    # Gather choice
    gather = Gather(
        num_digits=1,
        action="/voice/handle-choice",
        method="POST",
        timeout=10
    )
    response.append(gather)
    
    # Default to human
    fallback_url = generate_speech("I didn't receive a selection. Transferring you to a human now.")
    response.play(fallback_url)
    response.dial(HUMAN_PHONE)
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.post("/voice/handle-choice")
async def handle_choice(request: Request):
    """Handle user choice with dynamic AI conversation"""
    
    form_data = await request.form()
    choice = form_data.get('Digits')
    from_number = form_data.get('From')
    call_sid = form_data.get('CallSid')
    
    print(f"📱 Choice: {choice} from {from_number}")
    
    response = VoiceResponse()
    
    if choice == '1':
        # Start AI conversation with YOUR voice
        ai_text = get_ai_response(call_sid, "User wants to talk to AI", "greeting")
        audio_url = generate_speech(ai_text)
        response.play(audio_url)
        
        # Start conversation flow
        response.redirect("/voice/conversation")
        
    elif choice == '2':
        # Transfer to human
        notify_human_transfer(from_number, call_sid, "Initial choice")
        transfer_text = "Perfect! Transferring you to a human team member now."
        audio_url = generate_speech(transfer_text)
        response.play(audio_url)
        response.dial(HUMAN_PHONE)
        
    else:
        # Invalid
        fallback_text = "I didn't catch that. Let me transfer you to a human."
        audio_url = generate_speech(fallback_text)
        response.play(audio_url)
        response.dial(HUMAN_PHONE)
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.post("/voice/conversation")
async def conversation(request: Request):
    """Main conversation loop with dynamic AI responses"""
    
    form_data = await request.form()
    call_sid = form_data.get('CallSid')
    speech_result = form_data.get('SpeechResult', '')
    digits = form_data.get('Digits', '')
    
    response = VoiceResponse()
    
    # Check for human transfer request
    if '*' in digits or any(word in speech_result.lower() for word in ['human', 'person', 'representative', 'transfer']):
        transfer_text = "Of course, let me transfer you to a specialist now."
        audio_url = generate_speech(transfer_text)
        response.play(audio_url)
        response.dial(HUMAN_PHONE)
        return PlainTextResponse(content=str(response), media_type="application/xml")
    
    # Get AI response based on what they said
    if speech_result:
        ai_text = get_ai_response(call_sid, speech_result, "conversation")
        
        # Check if AI wants to transfer
        if "transfer" in ai_text.lower() or "specialist" in ai_text.lower():
            audio_url = generate_speech(ai_text)
            response.play(audio_url)
            response.dial(HUMAN_PHONE)
            return PlainTextResponse(content=str(response), media_type="application/xml")
        
        # Generate and play AI response with YOUR voice
        audio_url = generate_speech(ai_text)
        response.play(audio_url)
        
        # Continue conversation
        gather = Gather(
            input='speech dtmf',
            action='/voice/conversation',
            method='POST',
            speech_timeout='auto',
            timeout=5,
            finish_on_key='#'
        )
        response.append(gather)
        
    else:
        # No response - offer human
        fallback_text = "I didn't catch that. Would you like to speak with a human? Press 1 for yes, 2 to continue with me."
        audio_url = generate_speech(fallback_text)
        response.play(audio_url)
        
        gather = Gather(
            num_digits=1,
            action='/voice/fallback-choice',
            method='POST',
            timeout=5
        )
        response.append(gather)
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.post("/voice/fallback-choice")
async def fallback_choice(request: Request):
    """Handle fallback when they don't respond"""
    
    form_data = await request.form()
    choice = form_data.get('Digits')
    call_sid = form_data.get('CallSid')
    
    response = VoiceResponse()
    
    if choice == '1':
        # Transfer to human
        transfer_text = "Great, connecting you now."
        audio_url = generate_speech(transfer_text)
        response.play(audio_url)
        response.dial(HUMAN_PHONE)
    else:
        # Continue with AI
        continue_text = "Okay, let's continue. Tell me about your law firm."
        audio_url = generate_speech(continue_text)
        response.play(audio_url)
        response.redirect("/voice/conversation")
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.get("/test-tts")
async def test_tts():
    """Test endpoint to verify TTS loads correctly"""
    try:
        tts = get_tts()
        return {
            "status": "success",
            "message": "TTS loaded successfully",
            "model": "xtts_v2"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def notify_human_transfer(from_number: str, reason: str):
    """Send email notification"""
    try:
        params = {
            "from": os.getenv("FROM_EMAIL", "onboarding@resend.dev"),
            "to": [os.getenv("FROM_EMAIL")],
            "subject": f"🔔 Live Call Transfer - {from_number}",
            "html": f"""
            <h2>Live Call Transfer</h2>
            <p><strong>From:</strong> {from_number}</p>
            <p><strong>Reason:</strong> {reason}</p>
            <p><strong>Transferring to:</strong> {HUMAN_PHONE}</p>
            """
        }
        resend.Emails.send(params)
    except Exception as e:
        print(f"Email error: {e}")


def schedule_callback(name: str, phone: str, email: str, context: str):
    """Schedule callback"""
    try:
        params = {
            "from": os.getenv("FROM_EMAIL", "onboarding@resend.dev"),
            "to": [os.getenv("FROM_EMAIL")],
            "subject": f"🔔 Callback Request - {phone}",
            "html": f"""
            <h2>Callback Request</h2>
            <p><strong>Name:</strong> {name}</p>
            <p><strong>Phone:</strong> {phone}</p>
            <p><strong>Context:</strong> {context}</p>
            <p><strong>Action:</strong> Call back ASAP</p>
            """
        }
        resend.Emails.send(params)
        print(f"✅ Callback scheduled: {phone}")
    except Exception as e:
        print(f"Email error: {e}")