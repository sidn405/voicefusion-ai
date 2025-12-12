from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from flask import Flask, request
import torch
import torch.serialization
import os

# Add safe globals for XTTS
try:
    from TTS.tts.configs.xtts_config import XttsConfig
    torch.serialization.add_safe_globals([XttsConfig])
except ImportError:
    pass

from TTS.api import TTS

# Twilio credentials
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'your_account_sid')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'your_auth_token')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '+1234567890')

# Initialize Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Initialize Flask app for webhooks
app = Flask(__name__)

# Initialize TTS with your cloned voice
tts = None
REFERENCE_VOICE = "reference_voice.wav"  # Your voice recording

def load_tts():
    """Load TTS model with voice cloning"""
    global tts
    if tts is None:
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    return tts

def generate_speech(text: str, output_file: str = "response.wav"):
    """Generate speech using cloned voice"""
    model = load_tts()
    
    if os.path.exists(REFERENCE_VOICE):
        model.tts_to_file(
            text=text,
            file_path=output_file,
            speaker_wav=REFERENCE_VOICE,
            language="en"
        )
    else:
        model.tts_to_file(
            text=text,
            file_path=output_file,
            language="en"
        )
    
    return output_file

def make_cold_call(to_number: str, script: str):
    """
    Make an outbound cold call
    
    Args:
        to_number: Phone number to call (E.164 format: +1234567890)
        script: Opening script to say
    """
    try:
        # Generate TTS audio for the script
        audio_file = generate_speech(script)
        
        # Upload audio to a publicly accessible URL
        # You'll need to host this somewhere accessible
        audio_url = f"https://your-domain.com/audio/{audio_file}"
        
        # Make the call
        call = client.calls.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            url='https://your-domain.com/handle_call',  # Your webhook URL
            status_callback='https://your-domain.com/call_status',
            record=True  # Record the call
        )
        
        print(f"✅ Call initiated: {call.sid}")
        return call.sid
        
    except Exception as e:
        print(f"❌ Call failed: {e}")
        return None

@app.route("/handle_call", methods=['POST'])
def handle_call():
    """Handle incoming call webhook"""
    response = VoiceResponse()
    
    # Opening script
    opening_script = """
    Hello! This is Sidney from 4D Gaming. 
    I wanted to reach out about LawBot 360, 
    an AI-powered legal intake assistant that handles client intake 24/7.
    Do you have a minute to discuss how this could benefit your firm?
    """
    
    # Generate speech
    audio_file = generate_speech(opening_script.strip())
    
    # Play the audio (you need to host this publicly)
    response.play(f"https://your-domain.com/audio/{audio_file}")
    
    # Gather response
    gather = Gather(
        input='speech',
        action='/handle_response',
        timeout=5,
        speechTimeout='auto'
    )
    response.append(gather)
    
    # If no input
    response.say("I didn't catch that. Please call us back when you have time.")
    
    return str(response)

@app.route("/handle_response", methods=['POST'])
def handle_response():
    """Handle user's speech response"""
    response = VoiceResponse()
    
    # Get speech transcription
    speech_result = request.values.get('SpeechResult', '').lower()
    
    print(f"User said: {speech_result}")
    
    # Simple logic - you can make this more sophisticated
    if any(word in speech_result for word in ['yes', 'sure', 'interested']):
        follow_up = """
        Great! LawBot 360 handles intake 24/7, qualifies leads, 
        schedules consultations, and processes payments automatically.
        Most firms see 30 to 70 percent more booked consultations.
        Can I send you a demo link to see it in action?
        """
        audio_file = generate_speech(follow_up.strip())
        response.play(f"https://your-domain.com/audio/{audio_file}")
        
    elif any(word in speech_result for word in ['no', 'not interested', 'busy']):
        closing = "No problem! Have a great day."
        audio_file = generate_speech(closing)
        response.play(f"https://your-domain.com/audio/{audio_file}")
        
    else:
        clarification = "I didn't quite catch that. Are you interested in learning more?"
        audio_file = generate_speech(clarification)
        response.play(f"https://your-domain.com/audio/{audio_file}")
        
        gather = Gather(
            input='speech',
            action='/handle_response',
            timeout=5
        )
        response.append(gather)
    
    return str(response)

@app.route("/call_status", methods=['POST'])
def call_status():
    """Handle call status updates"""
    call_sid = request.values.get('CallSid')
    call_status = request.values.get('CallStatus')
    
    print(f"Call {call_sid} status: {call_status}")
    
    # Log to database or send notification
    return '', 200

if __name__ == "__main__":
    print("🚀 Cold Calling Bot Server")
    print(f"📞 Using Twilio number: {TWILIO_PHONE_NUMBER}")
    print(f"🎤 Voice reference: {REFERENCE_VOICE}")
    
    # Example: Make a test call
    # make_cold_call("+15551234567", "Hello, this is a test call.")
    
    # Start webhook server
    app.run(host='0.0.0.0', port=5000, debug=True)