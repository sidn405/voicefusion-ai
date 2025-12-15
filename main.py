"""
LawBot 360 Voice Sales Agent - FastAPI Backend with Lightweight TTS
Handles Twilio webhooks with dynamic AI conversation using pyttsx3
"""

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, FileResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import os
import resend
from openai import OpenAI
import uuid
from pathlib import Path
import pyttsx3

# Initialize FastAPI
app = FastAPI(title="LawBot 360 Voice Sales Agent")

# Create audio directory
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
SERVER_URL = os.getenv("SERVER_URL", "https://voicefusion-ai-production.up.railway.app")

# Initialize lightweight TTS
print("🎤 Initializing lightweight TTS...")
try:
    # Try to initialize with espeak driver explicitly
    tts_engine = pyttsx3.init(driverName='espeak')
    print("✅ Using espeak driver")
except Exception as e:
    print(f"⚠️  espeak failed: {e}, trying default driver...")
    try:
        tts_engine = pyttsx3.init()
        print("✅ Using default driver")
    except Exception as e2:
        print(f"❌ TTS initialization failed: {e2}")
        print("⚠️  TTS will use fallback (Twilio voice)")
        tts_engine = None

# Configure voice for sales calls (if TTS initialized successfully)
if tts_engine:
    try:
        voices = tts_engine.getProperty('voices')
        if voices and len(voices) > 1:
            tts_engine.setProperty('voice', voices[1].id)  # Female voice
        tts_engine.setProperty('rate', 145)  # Slightly slower for clarity
        tts_engine.setProperty('volume', 0.95)  # Clear and confident
        print("✅ TTS ready")
    except Exception as e:
        print(f"⚠️  TTS configuration warning: {e}")
else:
    print("⚠️  Running without TTS engine - will use Twilio voice fallback")

# Conversation memory
conversations = {}


def generate_speech(text: str) -> str:
    """Generate speech with lightweight pyttsx3 (instant!)"""
    
    print(f"🎙️ Generating speech: '{text[:50]}...'")
    
    # If TTS engine failed to initialize, return empty string (will trigger Twilio fallback)
    if tts_engine is None:
        print("⚠️  TTS engine not available, using Twilio voice fallback")
        return ""
    
    try:
        # Truncate if too long
        if len(text) > 500:
            text = text[:500]
        
        # Generate unique filename
        audio_id = str(uuid.uuid4())
        output_file = AUDIO_DIR / f"{audio_id}.wav"
        
        # Generate audio (fast!)
        tts_engine.save_to_file(text, str(output_file))
        tts_engine.runAndWait()
        
        # Return public URL for Twilio
        audio_url = f"{SERVER_URL}/audio/{audio_id}.wav"
        print(f"✅ Audio ready: {audio_url}")
        
        return audio_url
        
    except Exception as e:
        print(f"❌ TTS error: {e}")
        return ""


def get_ai_response(call_sid: str, user_input: str, stage: str) -> str:
    """Get AI response based on conversation context"""
    
    # Initialize conversation if needed
    if call_sid not in conversations:
        conversations[call_sid] = {
            "history": [],
            "stage": "greeting",
            "client_name": None,
            "firm_name": None,
            "pain_points": [],
            "interested": False
        }
    
    conv = conversations[call_sid]
    conv["history"].append({"role": "user", "content": user_input})
    
    # Build system prompt for sales bot
    system_prompt = f"""You are a professional sales representative for LawBot 360, an AI client intake system for law firms.

Current stage: {stage}
Client name: {conv.get('client_name', 'Unknown')}
Firm: {conv.get('firm_name', 'Unknown')}

YOUR GOAL: Sell LawBot 360 ($25,000 base price, $7,500 down payment)

CRITICAL RULES:
1. Keep responses VERY SHORT (1-2 sentences max) - this is a phone call
2. Sound natural and conversational - like a real sales person
3. Listen to what they say and respond personally
4. Move the conversation toward discovery → pain points → solution → close
5. If they want human, acknowledge and we'll transfer
6. Be confident but consultative, not pushy
7. Use their name when you know it

PRODUCT: LawBot 360
- 24/7 AI-powered client intake chatbot
- Automatic lead qualification and consultation scheduling
- Integrates with Clio, Salesforce, MyCase
- Customizable for any practice area
- Base price: $25,000 one-time, $7,500 down payment to start

CONVERSATION FLOW:
1. Opening: "Hi! Quick question - are you losing leads outside business hours?"
2. Discovery: Ask about their current intake process
3. Pain points: Identify what's not working
4. Solution: Show how LawBot 360 solves their specific problems
5. Pricing: Discuss investment when they're interested
6. Close: Get commitment or schedule demo

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
        "service": "LawBot 360 Voice Sales Agent",
        "tts": "pyttsx3" if tts_engine else "twilio-fallback",
        "tts_working": tts_engine is not None,
        "ai": "OpenAI GPT-4",
        "human_phone": HUMAN_PHONE,
        "deployment": "railway"
    }


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated audio files to Twilio"""
    audio_file = AUDIO_DIR / filename
    if audio_file.exists():
        return FileResponse(audio_file, media_type="audio/wav")
    return {"error": "Audio file not found"}


@app.post("/voice/inbound")
async def handle_inbound_call(request: Request):
    """Handle incoming call from interested law firm"""
    
    form_data = await request.form()
    from_number = form_data.get('From')
    call_sid = form_data.get('CallSid')
    
    print(f"📞 Incoming call from {from_number}")
    
    response = VoiceResponse()
    
    # Professional greeting
    greeting_text = ("Hi! Thanks for calling 4D Gaming about LawBot 360, "
                    "our AI-powered client intake system for law firms. "
                    "Press 1 to speak with our AI assistant, or press 2 to transfer to a human immediately.")
    
    greeting_url = generate_speech(greeting_text)
    
    if greeting_url:
        response.play(greeting_url)
    else:
        # Fallback to Twilio voice
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
    response.say("I didn't receive a selection. Transferring you to a human now.")
    response.dial(HUMAN_PHONE)
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.post("/voice/outbound/cold-call")
async def initiate_cold_call(request: Request):
    """Initiate outbound cold call (Twilio webhook entry point)"""
    
    form_data = await request.form()
    from_number = form_data.get('From')
    to_number = form_data.get('To')
    call_sid = form_data.get('CallSid')
    
    print(f"📞 Outbound cold call to {to_number}")
    
    response = VoiceResponse()
    
    # Opening pitch (direct and value-focused)
    opening_text = ("Hi! This is calling from 4D Gaming. "
                   "Quick question - are you losing leads outside business hours, nights and weekends? "
                   "We fix that with AI. Got 5 minutes?")
    
    opening_url = generate_speech(opening_text)
    
    if opening_url:
        response.play(opening_url)
    else:
        response.say(opening_text, voice="Polly.Joanna")
    
    # Gather yes/no response
    gather = Gather(
        input='speech dtmf',
        timeout=5,
        action='/voice/cold-call-response',
        method='POST'
    )
    response.append(gather)
    
    # If no response, leave voicemail
    voicemail_text = ("Hi, this is calling about LawBot 360. "
                     "We help law firms capture leads 24/7 with AI. "
                     "Visit lawbot360.com or call us back. Thanks!")
    
    voicemail_url = generate_speech(voicemail_text)
    if voicemail_url:
        response.play(voicemail_url)
    else:
        response.say(voicemail_text, voice="Polly.Joanna")
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.post("/voice/cold-call-response")
async def handle_cold_call_response(request: Request):
    """Handle response to cold call opening"""
    
    form_data = await request.form()
    speech_result = form_data.get('SpeechResult', '').lower()
    digits = form_data.get('Digits', '')
    call_sid = form_data.get('CallSid')
    
    response = VoiceResponse()
    
    # Check for interest
    interested_keywords = ['yes', 'sure', 'okay', 'interested', 'tell me', 'go ahead']
    not_interested_keywords = ['no', 'busy', 'not interested', 'remove', 'stop']
    
    if any(word in speech_result for word in interested_keywords) or digits == '1':
        # They're interested - start AI conversation
        ai_text = get_ai_response(call_sid, "Customer said yes to 5 minute pitch", "discovery")
        audio_url = generate_speech(ai_text)
        
        if audio_url:
            response.play(audio_url)
        else:
            response.say(ai_text, voice="Polly.Joanna")
        
        # Continue conversation
        response.redirect("/voice/conversation")
        
    elif any(word in speech_result for word in not_interested_keywords):
        # Not interested
        closing_text = "No problem. Have a great day!"
        closing_url = generate_speech(closing_text)
        
        if closing_url:
            response.play(closing_url)
        else:
            response.say(closing_text, voice="Polly.Joanna")
        
        response.hangup()
        
    else:
        # Unclear - ask again
        clarify_text = "Sorry, I didn't catch that. Do you have 5 minutes to hear how we can help? Press 1 for yes, 2 for no."
        clarify_url = generate_speech(clarify_text)
        
        if clarify_url:
            response.play(clarify_url)
        else:
            response.say(clarify_text, voice="Polly.Joanna")
        
        gather = Gather(
            num_digits=1,
            action='/voice/cold-call-response',
            timeout=5
        )
        response.append(gather)
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.post("/voice/handle-choice")
async def handle_choice(request: Request):
    """Handle user choice (AI or Human)"""
    
    form_data = await request.form()
    choice = form_data.get('Digits')
    from_number = form_data.get('From')
    call_sid = form_data.get('CallSid')
    
    print(f"📱 Choice: {choice} from {from_number}")
    
    response = VoiceResponse()
    
    if choice == '1':
        # Start AI conversation
        ai_text = get_ai_response(call_sid, "User chose AI assistant", "greeting")
        audio_url = generate_speech(ai_text)
        
        if audio_url:
            response.play(audio_url)
        else:
            response.say(ai_text, voice="Polly.Joanna")
        
        # Continue to conversation flow
        response.redirect("/voice/conversation")
        
    elif choice == '2':
        # Transfer to human
        notify_human_transfer(from_number, "User requested human from menu")
        
        transfer_text = "Perfect! Transferring you to a human team member now."
        audio_url = generate_speech(transfer_text)
        
        if audio_url:
            response.play(audio_url)
        else:
            response.say(transfer_text, voice="Polly.Joanna")
        
        response.dial(HUMAN_PHONE)
        
    else:
        # Invalid choice
        fallback_text = "I didn't catch that. Let me transfer you to a human."
        audio_url = generate_speech(fallback_text)
        
        if audio_url:
            response.play(audio_url)
        else:
            response.say(fallback_text, voice="Polly.Joanna")
        
        response.dial(HUMAN_PHONE)
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.post("/voice/conversation")
async def conversation(request: Request):
    """Main AI conversation loop"""
    
    form_data = await request.form()
    call_sid = form_data.get('CallSid')
    speech_result = form_data.get('SpeechResult', '')
    digits = form_data.get('Digits', '')
    
    response = VoiceResponse()
    
    # Check for human transfer request
    if '*' in digits or any(word in speech_result.lower() for word in ['human', 'person', 'representative', 'transfer']):
        transfer_text = "Of course, let me transfer you to a specialist now."
        audio_url = generate_speech(transfer_text)
        
        if audio_url:
            response.play(audio_url)
        else:
            response.say(transfer_text, voice="Polly.Joanna")
        
        notify_human_transfer(form_data.get('From'), "User requested transfer during conversation")
        response.dial(HUMAN_PHONE)
        return PlainTextResponse(content=str(response), media_type="application/xml")
    
    # Get AI response based on what they said
    if speech_result:
        ai_text = get_ai_response(call_sid, speech_result, "conversation")
        
        # Check if AI wants to transfer
        if "transfer" in ai_text.lower() or "specialist" in ai_text.lower():
            audio_url = generate_speech(ai_text)
            
            if audio_url:
                response.play(audio_url)
            else:
                response.say(ai_text, voice="Polly.Joanna")
            
            notify_human_transfer(form_data.get('From'), "AI determined human needed")
            response.dial(HUMAN_PHONE)
            return PlainTextResponse(content=str(response), media_type="application/xml")
        
        # Generate and play AI response
        audio_url = generate_speech(ai_text)
        
        if audio_url:
            response.play(audio_url)
        else:
            response.say(ai_text, voice="Polly.Joanna")
        
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
        
        if audio_url:
            response.play(audio_url)
        else:
            response.say(fallback_text, voice="Polly.Joanna")
        
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
    """Handle fallback when user doesn't respond"""
    
    form_data = await request.form()
    choice = form_data.get('Digits')
    call_sid = form_data.get('CallSid')
    
    response = VoiceResponse()
    
    if choice == '1':
        # Transfer to human
        transfer_text = "Great, connecting you now."
        audio_url = generate_speech(transfer_text)
        
        if audio_url:
            response.play(audio_url)
        else:
            response.say(transfer_text, voice="Polly.Joanna")
        
        notify_human_transfer(form_data.get('From'), "User chose human from fallback")
        response.dial(HUMAN_PHONE)
    else:
        # Continue with AI
        continue_text = "Okay, let's continue. Tell me about your law firm's current intake process."
        audio_url = generate_speech(continue_text)
        
        if audio_url:
            response.play(audio_url)
        else:
            response.say(continue_text, voice="Polly.Joanna")
        
        response.redirect("/voice/conversation")
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.get("/test-tts")
async def test_tts():
    """Test endpoint to verify TTS works"""
    if tts_engine is None:
        return {
            "status": "fallback",
            "message": "pyttsx3 not available, using Twilio voice",
            "engine": "twilio-polly",
            "quality": "Excellent (Amazon Polly)",
            "note": "This is fine! Twilio voice works great for sales calls."
        }
    
    try:
        test_text = "This is a test of the lightweight text to speech system. It's fast and reliable!"
        audio_url = generate_speech(test_text)
        
        if audio_url:
            return {
                "status": "success",
                "message": "pyttsx3 TTS working!",
                "engine": "pyttsx3 (espeak)",
                "test_audio": audio_url,
                "speed": "< 1 second"
            }
        else:
            return {
                "status": "error",
                "message": "TTS generation failed",
                "note": "Will fallback to Twilio voice in calls"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "note": "Will fallback to Twilio voice in calls"
        }


def notify_human_transfer(from_number: str, reason: str):
    """Send email notification for human transfer"""
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
            <p><strong>Action:</strong> Answer your phone!</p>
            """
        }
        resend.Emails.send(params)
        print(f"✅ Notified about transfer: {from_number}")
    except Exception as e:
        print(f"❌ Email notification error: {e}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)