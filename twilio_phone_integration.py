"""
Twilio Phone Integration for LawBot 360 Voice Sales Agent
Handles inbound and outbound calls
"""

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from flask import Flask, request, Response
import os
from lawbot_voice_sales_agent import VoiceSalesBot, ConversationStage

app = Flask(__name__)

# Initialize Twilio
twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

# Active conversations (in production, use Redis or database)
active_conversations = {}


@app.route("/voice/incoming", methods=['POST'])
def handle_incoming_call():
    """Handle incoming phone calls"""
    
    # Get caller information
    from_number = request.form.get('From')
    call_sid = request.form.get('CallSid')
    
    print(f"📞 Incoming call from {from_number}")
    
    # Create new conversation
    bot = VoiceSalesBot()
    active_conversations[call_sid] = bot
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Opening message
    opening = ("Hi! Thanks for calling 4D Gaming. I'm your AI assistant, and I'd love to tell you "
               "about LawBot 360, our AI-powered client intake system for law firms. "
               "Is this a good time to chat for a few minutes? Press 1 for yes, or 2 if you'd like "
               "me to call back at a better time.")
    
    gather = Gather(
        num_digits=1,
        action='/voice/handle-response',
        method='POST',
        timeout=5
    )
    gather.say(opening, voice='Polly.Matthew')
    
    response.append(gather)
    
    # If no input, repeat
    response.say("I didn't hear a response. Please press 1 to continue or 2 to schedule a callback.")
    response.redirect('/voice/incoming')
    
    return Response(str(response), mimetype='text/xml')


@app.route("/voice/handle-response", methods=['POST'])
def handle_response():
    """Handle user DTMF or speech responses"""
    
    call_sid = request.form.get('CallSid')
    digits = request.form.get('Digits')
    speech_result = request.form.get('SpeechResult')
    
    bot = active_conversations.get(call_sid)
    
    if not bot:
        # Conversation not found, restart
        response = VoiceResponse()
        response.say("I'm sorry, there was an error. Please call back.")
        response.hangup()
        return Response(str(response), mimetype='text/xml')
    
    response = VoiceResponse()
    
    # Handle DTMF input
    if digits:
        if digits == '1':
            # Continue conversation
            message = "Great! Let me start by getting your name. What should I call you?"
            response.say(message, voice='Polly.Matthew')
            response.record(
                action='/voice/process-recording',
                max_length=10,
                transcribe=True,
                transcribe_callback='/voice/transcription'
            )
        
        elif digits == '2':
            # Schedule callback
            message = "No problem! I'll have someone call you back at a better time. Thanks for your interest!"
            response.say(message, voice='Polly.Matthew')
            response.hangup()
        
        else:
            response.say("I didn't understand that. Please press 1 to continue or 2 for a callback.")
            response.redirect('/voice/handle-response')
    
    # Handle speech input
    elif speech_result:
        # Process with AI
        bot_response = bot.chat_with_claude(speech_result)
        
        # Convert to speech
        response.say(bot_response, voice='Polly.Matthew')
        
        # Continue listening
        response.record(
            action='/voice/process-recording',
            max_length=30,
            transcribe=True,
            transcribe_callback='/voice/transcription'
        )
    
    return Response(str(response), mimetype='text/xml')


@app.route("/voice/process-recording", methods=['POST'])
def process_recording():
    """Process recorded audio from user"""
    
    call_sid = request.form.get('CallSid')
    recording_url = request.form.get('RecordingUrl')
    
    bot = active_conversations.get(call_sid)
    
    if not bot:
        response = VoiceResponse()
        response.say("Session expired. Please call back.")
        response.hangup()
        return Response(str(response), mimetype='text/xml')
    
    # Wait for transcription (handled by callback)
    response = VoiceResponse()
    response.say("Please hold while I process that...", voice='Polly.Matthew')
    response.pause(length=2)
    response.redirect('/voice/continue-conversation')
    
    return Response(str(response), mimetype='text/xml')


@app.route("/voice/transcription", methods=['POST'])
def handle_transcription():
    """Handle transcription callback from Twilio"""
    
    call_sid = request.form.get('CallSid')
    transcription_text = request.form.get('TranscriptionText')
    
    bot = active_conversations.get(call_sid)
    
    if bot and transcription_text:
        # Store transcription for processing
        if not hasattr(bot, 'pending_transcription'):
            bot.pending_transcription = []
        bot.pending_transcription.append(transcription_text)
    
    return '', 200


@app.route("/voice/continue-conversation", methods=['POST'])
def continue_conversation():
    """Continue conversation after processing transcription"""
    
    call_sid = request.form.get('CallSid')
    bot = active_conversations.get(call_sid)
    
    if not bot:
        response = VoiceResponse()
        response.say("Session expired.")
        response.hangup()
        return Response(str(response), mimetype='text/xml')
    
    # Get latest transcription
    if hasattr(bot, 'pending_transcription') and bot.pending_transcription:
        user_input = bot.pending_transcription.pop(0)
        
        # Get AI response
        bot_response = bot.chat_with_claude(user_input)
        
        response = VoiceResponse()
        response.say(bot_response, voice='Polly.Matthew')
        
        # Check if conversation completed
        if bot.context.current_stage == ConversationStage.COMPLETED:
            response.say("Thanks for your time! We'll be in touch soon. Have a great day!")
            response.hangup()
            
            # Clean up
            bot.save_conversation()
            del active_conversations[call_sid]
        
        else:
            # Continue listening
            response.record(
                action='/voice/process-recording',
                max_length=30,
                transcribe=True,
                transcribe_callback='/voice/transcription'
            )
        
        return Response(str(response), mimetype='text/xml')
    
    # No transcription yet, wait
    response = VoiceResponse()
    response.pause(length=1)
    response.redirect('/voice/continue-conversation')
    return Response(str(response), mimetype='text/xml')


@app.route("/voice/status", methods=['POST'])
def call_status():
    """Handle call status updates"""
    
    call_sid = request.form.get('CallSid')
    call_status = request.form.get('CallStatus')
    
    print(f"Call {call_sid} status: {call_status}")
    
    # Clean up completed calls
    if call_status in ['completed', 'busy', 'no-answer', 'failed', 'canceled']:
        if call_sid in active_conversations:
            bot = active_conversations[call_sid]
            bot.save_conversation()
            del active_conversations[call_sid]
    
    return '', 200


def make_outbound_call(to_number: str, firm_name: str = None):
    """Make outbound sales call"""
    
    try:
        call = twilio_client.calls.create(
            to=to_number,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            url=f"{os.getenv('SERVER_URL')}/voice/outbound-greeting",
            status_callback=f"{os.getenv('SERVER_URL')}/voice/status",
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            record=True  # Record call for quality/training
        )
        
        print(f"📞 Outbound call initiated: {call.sid}")
        return call.sid
    
    except Exception as e:
        print(f"❌ Call failed: {e}")
        return None


@app.route("/voice/outbound-greeting", methods=['POST'])
def outbound_greeting():
    """Handle outbound call greeting"""
    
    call_sid = request.form.get('CallSid')
    
    # Create new conversation
    bot = VoiceSalesBot()
    active_conversations[call_sid] = bot
    
    response = VoiceResponse()
    
    greeting = ("Hi! This is calling from 4D Gaming. I'm reaching out to discuss how we can help "
                "your law firm capture more leads with our AI-powered intake system. "
                "Is this a good time to chat? Press 1 for yes, or 2 if I should call back later.")
    
    gather = Gather(
        num_digits=1,
        action='/voice/handle-response',
        timeout=5
    )
    gather.say(greeting, voice='Polly.Matthew')
    
    response.append(gather)
    response.say("I didn't hear a response. I'll try calling back another time. Thanks!")
    response.hangup()
    
    return Response(str(response), mimetype='text/xml')


@app.route("/voice/send-sms", methods=['POST'])
def send_sms():
    """Send SMS with portal link"""
    
    to_number = request.json.get('to')
    message_text = request.json.get('message')
    
    try:
        message = twilio_client.messages.create(
            to=to_number,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            body=message_text
        )
        
        return {'success': True, 'sid': message.sid}
    
    except Exception as e:
        return {'success': False, 'error': str(e)}, 400


if __name__ == "__main__":
    # Run Flask app
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)