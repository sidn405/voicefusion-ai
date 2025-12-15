"""
LawBot 360 Voice Sales Agent - FastAPI Backend with Replicate Voice Cloning
Handles Twilio webhooks with dynamic AI conversation using your cloned voice via Replicate API
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse, FileResponse
from twilio.twiml.voice_response import VoiceResponse, Dial, Gather
from twilio.rest import Client
import os
import resend
from openai import OpenAI
import requests
import uuid
from pathlib import Path

# Initialize FastAPI
app = FastAPI(title="LawBot 360 Voice Sales Agent")

# Create audio directory for downloaded files
AUDIO_DIR = Path("/tmp/audio")
AUDIO_DIR.mkdir(exist_ok=True)

# Initialize clients
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
TTS_SERVER_URL = os.getenv("TTS_SERVICE_URL")

# Cache for reference voice URL (upload once, reuse)
reference_voice_url = None

# Conversation memory
conversations = {}


def get_reference_voice_url() -> str:
    """Upload reference voice to Replicate and get URL (cache it)"""
    global reference_voice_url
    
    if reference_voice_url is None:
        # Serve reference voice from our server
        reference_voice_url = f"{SERVER_URL}/reference-voice"
        print(f"🎤 Using reference voice URL: {reference_voice_url}")
    
    return reference_voice_url


def generate_speech(text: str) -> str:
    """Generate speech with cloned voice using Replicate REST API (avoids SDK issues!)"""
    
    print(f"🎙️ Generating speech via Replicate REST API: '{text[:50]}...'")
    
    try:
        # Use publicly accessible URL for reference voice
        reference_voice_url = f"{SERVER_URL}/reference-voice"
        
        print(f"🎤 Using reference voice from: {reference_voice_url}")
        
        # Call Replicate REST API directly (avoid Python SDK serialization issues)
        api_token = os.getenv("REPLICATE_API_TOKEN")
        
        # Create prediction via REST API
        headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "version": "684bc3855b37866c0c65add2ff39c78f3dea3f4ff103a436465326e0f438d55e",
            "input": {
                "text": text,
                "speaker": reference_voice_url,  # Public URL
                "language": "en"
            }
        }
        
        print(f"🚀 Sending prediction request to Replicate...")
        # Call TTS service via internal Railway network
        response = requests.post(
            f"{TTS_SERVER_URL}/generate",
            json={"text": text},
            timeout=10
        )
        response.raise_for_status()
        
        prediction = response.json()
        prediction_id = prediction["id"]
        prediction_url = prediction["urls"]["get"]
        
        print(f"⏳ Waiting for prediction {prediction_id}...")
        
        # Poll for completion
        max_attempts = 60  # 60 seconds timeout
        for attempt in range(max_attempts):
            import time
            time.sleep(1)
            
            status_response = requests.get(prediction_url, headers=headers, timeout=10)
            status_response.raise_for_status()
            status_data = status_response.json()
            
            if status_data["status"] == "succeeded":
                output_url = status_data["output"]
                print(f"✅ Replicate succeeded! Output: {output_url}")
                
                # Download generated audio
                audio_id = str(uuid.uuid4())
                output_file = AUDIO_DIR / f"{audio_id}.wav"
                
                print(f"📥 Downloading audio...")
                audio_response = requests.get(output_url, timeout=60)
                audio_response.raise_for_status()
                
                with open(output_file, "wb") as f:
                    f.write(audio_response.content)
                
                # Return public URL for Twilio to play
                audio_url = f"{SERVER_URL}/audio/{audio_id}.wav"
                print(f"✅ Audio ready: {audio_url}")
                
                return audio_url
                
            elif status_data["status"] == "failed":
                print(f"❌ Replicate prediction failed: {status_data.get('error')}")
                return ""
                
            # Still processing, continue polling
        
        print(f"❌ Replicate timeout after {max_attempts} seconds")
        return ""
        
    except Exception as e:
        print(f"❌ Replicate error: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return ""


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
        "service": "LawBot 360 Voice Sales Agent - Replicate Voice Cloning",
        "voice_cloning": "enabled (via Replicate API)",
        "human_phone": HUMAN_PHONE,
        "no_scipy_issues": True
    }


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated audio files to Twilio"""
    audio_file = AUDIO_DIR / filename
    if audio_file.exists():
        return FileResponse(audio_file, media_type="audio/wav")
    return {"error": "Audio file not found"}


@app.get("/reference-voice")
async def serve_reference_voice():
    """Serve reference voice file to Replicate"""
    if os.path.exists(REFERENCE_VOICE):
        return FileResponse(REFERENCE_VOICE, media_type="audio/wav")
    return {"error": "Reference voice not found"}


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
    
    if greeting_url:
        # Use your cloned voice
        response.play(greeting_url)
    else:
        # Fallback to Twilio voice if Replicate fails
        print("⚠️ Falling back to Twilio voice")
        response.say(greeting_text, voice="Polly.Joanna")
    
    # Gather choice
    gather = Gather(
        num_digits=1,
        action="/voice/handle-choice",
        method="POST",
        timeout=10
    )
    response.append(gather)
    
    # Default to human
    fallback_text = "I didn't receive a selection. Transferring you to a human now."
    fallback_url = generate_speech(fallback_text)
    
    if fallback_url:
        response.play(fallback_url)
    else:
        response.say(fallback_text, voice="Polly.Joanna")
    
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
    """Test endpoint to verify Replicate voice cloning works"""
    try:
        # Test generating speech
        test_text = "This is a test of your cloned voice using Replicate API."
        audio_url = generate_speech(test_text)
        
        if audio_url:
            return {
                "status": "success",
                "message": "Replicate voice cloning working!",
                "model": "xtts-v2 (via Replicate)",
                "test_audio": audio_url
            }
        else:
            return {
                "status": "error",
                "message": "Failed to generate audio"
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