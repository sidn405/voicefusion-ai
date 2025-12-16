"""
LawBot 360 Voice Sales Agent - FastAPI Backend
Uses Twilio's built-in voices (Amazon Polly) - Professional quality, zero issues!
"""

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import os
import resend
from openai import OpenAI

# Initialize FastAPI
app = FastAPI(title="LawBot 360 Voice Sales Agent")

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

# Conversation memory
conversations = {}

# Twilio voice configuration (Amazon Polly voices)
# Options: Polly.Joanna (female), Polly.Matthew (male), Polly.Salli (female)
VOICE = "Polly.Joanna"  # Professional female voice


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

YOUR GOAL: Have a natural sales conversation about LawBot 360 ($25,000 base price, $7,500 down payment)

CRITICAL RULES:
1. Keep responses EXTREMELY SHORT (1-2 sentences max) - this is a phone call
2. Sound natural and conversational - like calling a friend
3. Ask ONE question at a time and wait for their answer
4. Don't mention transferring to humans - you ARE the conversation
5. Use their name when you know it
6. Be warm, confident, and consultative (not pushy)

PRODUCT: LawBot 360
- 24/7 AI-powered client intake chatbot
- Automatic lead qualification and consultation scheduling
- Integrates with Clio, Salesforce, MyCase
- Customizable for any practice area
- Base price: $25,000 one-time, $7,500 down to start

CONVERSATION FLOW:
1. Opening: "Great! I'm here to help. Quick question - are you currently losing leads when your office is closed?"
2. Discovery: Ask about their current intake process (ONE question at a time)
3. Pain points: Listen and identify what's not working
4. Solution: Show how LawBot 360 solves THEIR specific problems
5. Pricing: Discuss investment only when they're interested
6. Close: Get commitment or schedule a demo

Remember: SHORT responses, ONE question at a time, natural and friendly!
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
            max_tokens=80  # Even shorter - force brevity!
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
        "voice": f"Twilio ({VOICE})",
        "voice_quality": "Amazon Polly - Professional",
        "ai": "OpenAI GPT-4",
        "human_phone": HUMAN_PHONE,
        "deployment": "railway",
        "tts": "twilio-native"
    }


@app.post("/voice/inbound")
async def handle_inbound_call(request: Request):
    """Handle incoming call from interested law firm"""
    
    form_data = await request.form()
    from_number = form_data.get('From')
    call_sid = form_data.get('CallSid')
    
    print(f"📞 Incoming call from {from_number}")
    
    response = VoiceResponse()
    
    # Professional greeting with clear options
    greeting_text = ("Hi! Thanks for calling 4D Gaming about LawBot 360. "
                    "Press 1 to speak with me about our AI client intake system, "
                    "or press 2 to speak with a human team member right away.")
    
    response.say(greeting_text, voice=VOICE)
    
    # Gather choice
    gather = Gather(
        num_digits=1,
        action="/voice/handle-choice",
        method="POST",
        timeout=10
    )
    response.append(gather)
    
    # Default to human if no response
    response.say("I didn't receive a selection. Transferring you now.", voice=VOICE)
    response.dial(HUMAN_PHONE)
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.post("/voice/outbound/cold-call")
async def initiate_cold_call(request: Request):
    """Initiate outbound cold call (Twilio webhook entry point)"""
    
    form_data = await request.form()
    to_number = form_data.get('To')
    call_sid = form_data.get('CallSid')
    
    print(f"📞 Outbound cold call to {to_number}")
    
    response = VoiceResponse()
    
    # Opening pitch (direct and value-focused)
    opening_text = ("Hi! This is calling from 4D Gaming. "
                   "Quick question - are you losing leads outside business hours, nights and weekends? "
                   "We fix that with AI. Got 5 minutes?")
    
    response.say(opening_text, voice=VOICE)
    
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
    
    response.say(voicemail_text, voice=VOICE)
    
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
        response.say(ai_text, voice=VOICE)
        
        # Continue conversation
        response.redirect("/voice/conversation")
        
    elif any(word in speech_result for word in not_interested_keywords):
        # Not interested
        response.say("No problem. Have a great day!", voice=VOICE)
        response.hangup()
        
    else:
        # Unclear - ask again
        response.say("Sorry, I didn't catch that. Do you have 5 minutes to hear how we can help? Press 1 for yes, 2 for no.", voice=VOICE)
        
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
        # Start AI conversation naturally
        ai_text = get_ai_response(call_sid, "User chose AI assistant to learn about LawBot 360", "greeting")
        response.say(ai_text, voice=VOICE)
        
        # Listen for their response
        gather = Gather(
            input='speech',
            action='/voice/conversation',
            method='POST',
            speech_timeout='auto',
            timeout=10
        )
        response.append(gather)
        
        # If no response, prompt
        response.say("I'm here to help. What would you like to know?", voice=VOICE)
        
        # Try again
        gather2 = Gather(
            input='speech',
            action='/voice/conversation',
            method='POST',
            timeout=10
        )
        response.append(gather2)
        
        # Still no response - transfer
        response.say("Let me connect you with someone who can help.", voice=VOICE)
        notify_human_transfer(from_number, call_sid, "No response after initial greeting")
        response.dial(HUMAN_PHONE)
        
    elif choice == '2':
        # Transfer to human
        notify_human_transfer(from_number, call_sid, "User requested human from menu")
        response.say("Connecting you now.", voice=VOICE)
        response.dial(HUMAN_PHONE)
        
    else:
        # Invalid choice - transfer to human
        response.say("Let me transfer you to a team member.", voice=VOICE)
        notify_human_transfer(from_number, call_sid, "Invalid menu choice")
        response.dial(HUMAN_PHONE)
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.post("/voice/conversation")
async def conversation(request: Request):
    """Main AI conversation loop"""
    
    form_data = await request.form()
    call_sid = form_data.get('CallSid')
    speech_result = form_data.get('SpeechResult', '')
    digits = form_data.get('Digits', '')
    from_number = form_data.get('From')
    
    response = VoiceResponse()
    
    # Check for human transfer request (user says "human" or presses *)
    if '*' in digits or any(word in speech_result.lower() for word in ['human', 'person', 'representative', 'transfer']):
        response.say("Of course, let me transfer you to a specialist now.", voice=VOICE)
        notify_human_transfer(from_number, call_sid, "User requested transfer during conversation")
        response.dial(HUMAN_PHONE)
        return PlainTextResponse(content=str(response), media_type="application/xml")
    
    # Get AI response based on what they said
    if speech_result:
        print(f"📞 User said: {speech_result}")
        ai_text = get_ai_response(call_sid, speech_result, "conversation")
        print(f"🤖 AI responding: {ai_text}")
        
        # Check if AI wants to transfer
        if "transfer" in ai_text.lower() or "specialist" in ai_text.lower():
            response.say(ai_text, voice=VOICE)
            notify_human_transfer(from_number, call_sid, "AI determined human needed")
            response.dial(HUMAN_PHONE)
            return PlainTextResponse(content=str(response), media_type="application/xml")
        
        # Say AI response
        response.say(ai_text, voice=VOICE)
        
        # Continue conversation - wait for their response
        gather = Gather(
            input='speech',  # Only speech (no DTMF needed during conversation)
            action='/voice/conversation',
            method='POST',
            speech_timeout='auto',  # Auto-detect when they stop talking
            timeout=10,  # Wait up to 10 seconds for them to start talking
            finish_on_key='#'
        )
        response.append(gather)
        
        # If they don't respond after timeout, prompt again
        response.say("Are you still there?", voice=VOICE)
        
        # Give them another chance
        gather2 = Gather(
            input='speech',
            action='/voice/conversation',
            method='POST',
            timeout=10
        )
        response.append(gather2)
        
        # If still no response, offer human
        response.say("I'm having trouble hearing you. Let me transfer you to someone who can help.", voice=VOICE)
        notify_human_transfer(from_number, call_sid, "No response after multiple attempts")
        response.dial(HUMAN_PHONE)
        
    else:
        # No speech detected at all
        print("⚠️ No speech result received")
        response.say("I'm sorry, I didn't hear anything. Let me connect you with a human specialist.", voice=VOICE)
        notify_human_transfer(from_number, call_sid, "No speech detected")
        response.dial(HUMAN_PHONE)
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.post("/voice/fallback-choice")
async def fallback_choice(request: Request):
    """Handle fallback when user doesn't respond"""
    
    form_data = await request.form()
    choice = form_data.get('Digits')
    call_sid = form_data.get('CallSid')
    from_number = form_data.get('From')
    
    response = VoiceResponse()
    
    if choice == '1':
        # Transfer to human
        response.say("Great, connecting you now.", voice=VOICE)
        notify_human_transfer(from_number, call_sid, "User chose human from fallback")
        response.dial(HUMAN_PHONE)
    else:
        # Continue with AI
        response.say("Okay, let's continue. Tell me about your law firm's current intake process.", voice=VOICE)
        
        # Listen for response
        gather = Gather(
            input='speech',
            action='/voice/conversation',
            method='POST',
            timeout=10
        )
        response.append(gather)
        
        # If still no response, transfer
        response.say("Let me connect you with someone.", voice=VOICE)
        notify_human_transfer(from_number, call_sid, "Multiple failed attempts")
        response.dial(HUMAN_PHONE)
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


def notify_human_transfer(from_number: str, call_sid: str, reason: str):
    """Send email notification with conversation transcript"""
    try:
        # Get conversation history if available
        conversation_html = "<p><em>No conversation history available</em></p>"
        
        if call_sid in conversations:
            conv = conversations[call_sid]
            if conv["history"]:
                conversation_html = "<h3>Conversation Transcript:</h3><div style='background: #f5f5f5; padding: 15px; border-radius: 5px;'>"
                
                for msg in conv["history"]:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    
                    if role == "user":
                        conversation_html += f"<p><strong>Prospect:</strong> {content}</p>"
                    elif role == "assistant":
                        conversation_html += f"<p><strong>AI Bot:</strong> {content}</p>"
                
                conversation_html += "</div>"
                
                # Add context info
                if conv.get("client_name"):
                    conversation_html += f"<p><strong>Client Name:</strong> {conv['client_name']}</p>"
                if conv.get("firm_name"):
                    conversation_html += f"<p><strong>Firm Name:</strong> {conv['firm_name']}</p>"
                if conv.get("pain_points"):
                    conversation_html += f"<p><strong>Pain Points Mentioned:</strong> {', '.join(conv['pain_points'])}</p>"
        
        params = {
            "from": os.getenv("FROM_EMAIL", "onboarding@resend.dev"),
            "to": [os.getenv("FROM_EMAIL")],
            "subject": f"🔔 Live Call Transfer - {from_number}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px;">
                <h2 style="color: #667eea;">🔔 Live Call Transfer</h2>
                
                <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0; font-weight: bold; color: #856404;">
                        ⚡ INCOMING CALL - Answer your phone now!
                    </p>
                </div>
                
                <h3>Call Details:</h3>
                <ul>
                    <li><strong>From:</strong> {from_number}</li>
                    <li><strong>Reason:</strong> {reason}</li>
                    <li><strong>Call SID:</strong> {call_sid}</li>
                    <li><strong>Your Number:</strong> {HUMAN_PHONE}</li>
                </ul>
                
                {conversation_html}
                
                <div style="background: #e7f3ff; padding: 15px; border-radius: 5px; margin-top: 20px;">
                    <p><strong>📞 Next Steps:</strong></p>
                    <ol>
                        <li>Answer the incoming call on {HUMAN_PHONE}</li>
                        <li>Review the conversation above to see where the bot left off</li>
                        <li>Continue the conversation naturally</li>
                        <li>Close the deal! 💰</li>
                    </ol>
                </div>
                
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    This is an automated notification from LawBot 360 Sales Bot
                </p>
            </div>
            """
        }
        resend.Emails.send(params)
        print(f"✅ Notified about transfer: {from_number}")
        print(f"📧 Email sent with conversation transcript")
    except Exception as e:
        print(f"❌ Email notification error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    print("=" * 70)
    print("🤖 LawBot 360 Voice Sales Agent")
    print("=" * 70)
    print(f"Voice: {VOICE} (Amazon Polly)")
    print(f"AI: OpenAI GPT-4")
    print(f"Port: {port}")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=port)