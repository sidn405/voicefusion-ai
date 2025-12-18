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

# Validate phone number format on startup
if HUMAN_PHONE:
    # Clean phone number - ensure it's in E.164 format
    if not HUMAN_PHONE.startswith('+'):
        print(f"⚠️  WARNING: PHONE number should start with + (E.164 format)")
        print(f"   Current: {HUMAN_PHONE}")
        print(f"   Should be: +15043833692")
    else:
        print(f"✅ Human transfer number configured: {HUMAN_PHONE}")
else:
    print("❌ WARNING: PHONE environment variable not set! Transfers will fail.")
    print("   Set in Railway: PHONE=+15043833692")
SERVER_URL = os.getenv("SERVER_URL", "https://voicefusion-ai-production.up.railway.app")

# Conversation memory
conversations = {}

# Deduplication tracking (prevent duplicate emails)
sent_notifications = set()  # Track transfer notifications by call_sid
sent_integration_forms = set()  # Track integration forms by email+project_id

# Twilio voice configuration (Amazon Polly voices)
# Options: Polly.Joanna (female), Polly.Matthew (male), Polly.Salli (female)
VOICE = "Polly.Joanna"  # Professional female voice


def transfer_to_human(response: VoiceResponse, reason: str = "Transfer requested"):
    """Helper function to transfer call with proper error handling"""
    if not HUMAN_PHONE:
        print(f"❌ Cannot transfer: PHONE not configured")
        response.say("I apologize, but I'm unable to transfer you right now. Please call us directly at 504-383-3692.", voice=VOICE)
        return response
    
    print(f"🔄 Transferring to {HUMAN_PHONE}. Reason: {reason}")
    
    try:
        response.dial(
            number=HUMAN_PHONE,
            timeout=30,
            action='/voice/dial-status',
            method='POST'
        )
    except Exception as e:
        print(f"❌ Dial error: {e}")
        response.say("I'm having trouble connecting. Please call us directly at 504-383-3692.", voice=VOICE)
    
    return response


def get_ai_response(call_sid: str, user_input: str, stage: str) -> str:
    """Get AI response based on conversation context"""
    
    # Initialize conversation if needed
    if call_sid not in conversations:
        conversations[call_sid] = {
            "history": [],
            "stage": "greeting",
            "phase": "SALES",  # Start in SALES phase
            "current_step": 1,
            "committed": False,
            "client_name": None,
            "firm_name": None,
            "email": None,
            "phone_number": None,  # Will be populated from caller ID
            "selected_addons": [],
            "selected_maintenance": None,
            "payment_completed": False,
            "payment_confirmed_by_webhook": False,  # Only true when webhook confirms
            "silence_count": 0  # Track how many times we've had silence
        }
    
    conv = conversations[call_sid]
    conv["history"].append({"role": "user", "content": user_input})
    
    # Detect if they've committed to moving forward
    # Strip punctuation for better matching
    user_input_clean = user_input.lower().strip().rstrip('.,!?;')
    
    # Affirmative responses that indicate interest
    affirmative_responses = ['yes', 'yeah', 'yep', 'yup', 'sure', 'okay', 'ok', 'definitely',
                            'absolutely', 'let\'s do it', 'i\'m interested', 'sounds good', 
                            'that works', 'i\'d like that', 'i want it', 'let\'s get started']
    
    # Check if we should switch from SALES to ONBOARDING phase
    if conv["phase"] == "SALES" and user_input_clean in affirmative_responses:
        # User gave a clear affirmative response
        
        # Get last 2 bot messages to check what kind of question was asked
        recent_bot_messages = [msg.get('content', '') for msg in conv["history"][-4:] 
                              if msg.get('role') == 'assistant']
        last_bot_message = recent_bot_messages[-1] if recent_bot_messages else ""
        
        # CLOSING QUESTIONS - These indicate we're asking for commitment
        closing_indicators = [
            'interested in learning more',
            'does that sound',
            'would that help',
            'sound like it would help',
            'make sense for your',
            'ready to',
            'want to get started',
            'shall we get',
            'would you like',
            'does this sound',
            'would this help',
            'sound helpful',
            'sound like a good fit',
            'let\'s get you set up',  # Strong closing phrase
            'let\'s get started',
            'start capturing those leads',
            'get you set up'
        ]
        
        # DISCOVERY QUESTIONS - These are just gathering info, NOT asking for commitment
        discovery_indicators = [
            'are you losing leads',
            'do you have',
            'are you currently',
            'does your office',
            'how does your',
            'what happens when',
            'do leads',
            'does your receptionist',
            'after hours',
            'outside business hours'
        ]
        
        # Check if last bot message was a closing question (not discovery)
        is_closing_question = any(indicator in last_bot_message.lower() for indicator in closing_indicators)
        is_discovery_question = any(indicator in last_bot_message.lower() for indicator in discovery_indicators)
        
        # Only switch if it's a closing question (NOT a discovery question)
        if is_closing_question and not is_discovery_question:
            conv["committed"] = True
            conv["phase"] = "ONBOARDING"
            conv["current_step"] = 1
            print(f"✅ CLOSING QUESTION + YES: Switching to ONBOARDING")
            print(f"   Bot asked: '{last_bot_message[:100]}...'")
            print(f"   User said: '{user_input}'")
        else:
            # It's a discovery question or unclear - stay in SALES mode
            print(f"🔍 Discovery question answered - staying in SALES mode")
            print(f"   Question was: '{last_bot_message[:100]}...'")
            print(f"   User answered: '{user_input}'")
    
    # Build system prompt based on phase
    silence_context = ""
    if stage == "conversation" and len(conv["history"]) > 2:
        # Check if bot recently said "Are you still there?"
        recent_bot_messages = [msg.get('content', '') for msg in conv["history"][-3:] 
                              if msg.get('role') == 'assistant']
        if any('still there' in msg.lower() for msg in recent_bot_messages):
            silence_context = "\n\nNOTE: User had brief silence but is now responding. Acknowledge naturally and continue conversation without making a big deal of it."
    
    if conv["phase"] == "SALES":
        system_prompt = f"""You are a professional sales representative for LawBot 360, an AI client intake system for law firms.

Current stage: {stage}
Client name: {conv.get('client_name', 'Unknown')}
Firm: {conv.get('firm_name', 'Unknown')}
Phase: SALES MODE - Building Value

YOUR GOAL: Build interest and value, then transition to setup when they show interest

CRITICAL RULES:
1. Be PROFESSIONAL and CONSULTATIVE - you're a trusted advisor, not pushy
2. Keep responses SHORT (1-2 sentences max) - this is a phone call
3. NEVER MENTION PRICING - they'll see it in the portal
4. Focus on BENEFITS and ROI, not features
5. Ask questions to understand their needs
6. When they show interest → transition to setup
7. Be warm, confident, and helpful

PRODUCT: LawBot 360
- 24/7 AI-powered client intake chatbot
- Automatic lead qualification and consultation scheduling
- Integrates with Clio, Salesforce, MyCase
- Customizable for any practice area
- Proven to increase client intake by 40%

CONSULTATIVE APPROACH:
1. Opening: "Great! I'm here to help. Quick question - are you currently losing leads when your office is closed?"
2. Discovery: Ask about their current intake process (ONE question at a time)
3. Pain points: Listen and identify what's not working
4. Solution: "LawBot 360 handles that 24/7 - our clients see 40% more consultations"
5. Value: "If you could capture even 2-3 more quality leads per month, that would be significant, right?"
6. Trial close: "Does that sound like it would help your firm?"
7. When they say YES → Transition: "Perfect! Let's get you set up right now so you can start capturing those leads."

HANDLING SHORT RESPONSES:
- If they say just "yes", "yeah", "sure", "okay" → ALWAYS respond positively and move forward
- Example: User says "Yes" → You say "Perfect! Let me show you how this works for your firm specifically..."
- NEVER leave a "yes" response hanging - always acknowledge and continue
- If you asked a question and they answered affirmatively, ACT ON IT

NEVER MENTION:
- ❌ Pricing or costs ($7,500, $25,000, etc.)
- ❌ Down payments
- ❌ Payment terms
- ❌ Specific dollar amounts
- ❌ "Investment" or "cost"

Instead focus on:
- ✅ Benefits (24/7 coverage, more clients)
- ✅ ROI (more cases captured)
- ✅ Pain relief (no more missed leads)
- ✅ Value (how it helps their practice)

OBJECTION HANDLING (without mentioning price):
- "How much does it cost?" → "Great question! You'll see all the details when we get you set up. First, does the concept make sense for your practice?"
- "Is it expensive?" → "It's an investment in growing your practice. Most firms see it pay for itself quickly. Let's get you set up and you can see all the options."
- "What's the price?" → "I'll show you everything when we set you up. But tell me - if you could capture 40% more leads, would that be valuable?"

Remember: Build VALUE, then transition to setup. Never discuss pricing!
{silence_context}
"""
    
    else:  # ONBOARDING phase
        system_prompt = f"""You are a patient, helpful onboarding specialist for 4D Gaming.

Current stage: {stage}
Current step: {conv.get('current_step', 1)}/14
Client name: {conv.get('client_name', 'Unknown')}
Firm: {conv.get('firm_name', 'Unknown')}
Phase: ONBOARDING MODE

YOUR GOAL: Walk them through COMPLETE setup - from portal login to payment completion

CRITICAL: If user just said "yes" or showed interest, START IMMEDIATELY with Step 1!
Don't ask if they're ready - they already said yes! Just begin the onboarding.

WHEN FIRST ENTERING ONBOARDING (user just committed):
- Immediately respond with: "Perfect! Let's get you set up right now. Open your browser and go to 4dgaming.games/client-portal.html. Tell me when you have it open."
- Do NOT ask "Are you ready?" or "Shall we begin?" - they already committed!
- Do NOT hesitate or wait - start Step 1 immediately

ONBOARDING RULES:
1. Be PATIENT and FRIENDLY - guide them gently
2. ONE step at a time - wait for confirmation
3. Keep responses SHORT (1-2 sentences)
4. Answer questions about features thoroughly
5. Let THEM discover pricing in the portal (don't mention it)
6. If they ask about add-on features, explain the benefits

ONBOARDING STEPS:

STEP 1: "Perfect! Let's get you set up right now. Open your browser and go to 4dgaming.games/client-portal.html. Tell me when you have it open."

STEP 2: "Great! Now create your account or log in if you have one. Let me know when you're in."

STEP 3: "Excellent! Scroll down and look for 'Start a new project'. Do you see it?"

STEP 4: "Perfect! Click the dropdown for 'Select service', then scroll down and choose 'LawBot 360'. Tell me when you've selected it."

STEP 5: "Great! Where it says 'Project name', enter your firm's name. What's your firm name?"

STEP 6: "Good! Fill in 'Brief description' - just describe what you need for your practice. Then complete 'Project details'. Let me know when you're ready."

STEP 7: "Now you'll see Optional Features - add-ons you might want:
- Native iOS & Android apps - gives your clients mobile access
- Multi-language support - serve diverse communities
- Advanced Analytics - track your ROI and performance
- SMS/WhatsApp integration - reach clients where they are
- Multi-location support - for firms with multiple offices
Would you like any of these add-ons? If you're not sure, you can skip them."

STEP 8: "Perfect! Now choose a Monthly Maintenance Plan:
- Basic: Hosting, security updates, bug fixes, email support
- Professional: Everything in Basic plus priority support and monthly feature updates  
- Enterprise: Everything plus 24/7 support and custom feature development
Or you can select 'No Maintenance Plan' if you prefer to handle it yourself.
Which makes sense for your firm?"

STEP 9: "Excellent! Click the 'Create Project' button. Let me know when it's created."

STEP 10: "Great! Look at the right side of your screen for the project summary. Do you see it?"

STEP 11: "Perfect! If you have any files to upload or messages to add, you can click 'Browse'. Otherwise, we can move to payment. Ready to continue?"

STEP 12: "Excellent! You'll see the 'Fund Milestone 1' button with your total amount. Click it and you'll be taken to our secure Stripe payment page. The payment includes everything you selected. Let me know when you're on the payment page."

STEP 13: "Take your time completing the payment. I'm right here if you have questions. Let me know when it's done."

STEP 14: "Congratulations! Your payment is complete. Here's what happens next:
- Our team reviews your project within 24 hours
- You'll receive your project timeline and start date  
- Setup takes 2 weeks
- You'll receive the integration form via email shortly

Do you have any questions about the process or your new LawBot 360 system?"

Remember: Be PATIENT, HELPFUL, ONE STEP AT A TIME. They'll see pricing in the portal naturally.
{silence_context}
"""
    
    # Get AI response
    messages = [
        {"role": "system", "content": system_prompt}
    ] + conv["history"][-15:]
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            temperature=0.7,
            max_tokens=120
        )
        
        ai_response = response.choices[0].message.content
        conv["history"].append({"role": "assistant", "content": ai_response})
        
        # Track onboarding step progression
        if conv["phase"] == "ONBOARDING":
            response_lower = ai_response.lower()
            if "4dgaming.games/client-portal" in response_lower:
                conv["current_step"] = 1
            elif "create your account" in response_lower or "log in" in response_lower:
                conv["current_step"] = 2
            elif "start a new project" in response_lower:
                conv["current_step"] = 3
            elif "select service" in response_lower or "choose 'lawbot" in response_lower:
                conv["current_step"] = 4
            elif "project name" in response_lower and "firm" in response_lower:
                conv["current_step"] = 5
            elif "brief description" in response_lower:
                conv["current_step"] = 6
            elif "optional features" in response_lower or "add-ons" in response_lower:
                conv["current_step"] = 7
            elif "maintenance plan" in response_lower:
                conv["current_step"] = 8
            elif "create project" in response_lower and "button" in response_lower:
                conv["current_step"] = 9
            elif "project summary" in response_lower:
                conv["current_step"] = 10
            elif "upload" in response_lower or "files" in response_lower or "browse" in response_lower:
                conv["current_step"] = 11
            elif "fund milestone" in response_lower or "payment page" in response_lower:
                conv["current_step"] = 12
            elif "take your time" in response_lower and "payment" in response_lower:
                conv["current_step"] = 13
            elif "congratulations" in response_lower:
                conv["current_step"] = 14
                conv["payment_completed"] = True
        
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
    transfer_to_human(response, "No selection received")
    
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
        transfer_to_human(response, "Transfer needed")
        
    elif choice == '2':
        # Transfer to human
        notify_human_transfer(from_number, call_sid, "User requested human from menu")
        response.say("Connecting you now.", voice=VOICE)
        transfer_to_human(response, "Transfer needed")
        
    else:
        # Invalid choice - transfer to human
        response.say("Let me transfer you to a team member.", voice=VOICE)
        notify_human_transfer(from_number, call_sid, "Invalid menu choice")
        transfer_to_human(response, "Transfer needed")
    
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
        transfer_to_human(response, "User requested")
        return PlainTextResponse(content=str(response), media_type="application/xml")
    
    # Get AI response based on what they said
    if speech_result:
        print(f"📞 User said: {speech_result}")
        print(f"🔍 Current phase: {conversations.get(call_sid, {}).get('phase', 'UNKNOWN')}")
        
        # Capture phone number (caller's number)
        if call_sid in conversations:
            conversations[call_sid]["phone_number"] = from_number
        
        # Check if user provided email address
        if "@" in speech_result and "." in speech_result:
            # Extract email from speech (rough extraction)
            words = speech_result.lower().split()
            for word in words:
                if "@" in word and "." in word:
                    if call_sid in conversations:
                        email = word.strip(".,!?")
                        conversations[call_sid]["email"] = email
                        print(f"📧 Email captured: {email}")
        
        # Check if user provided firm name
        if "firm" in speech_result.lower() or "law" in speech_result.lower():
            if call_sid in conversations:
                # Try to extract firm name (this is rough - might need refinement)
                conversations[call_sid]["firm_name"] = speech_result
        
        # NOTE: Payment confirmation now comes from webhook, not user speech
        # Removed automatic integration form sending based on keywords
        
        ai_text = get_ai_response(call_sid, speech_result, "conversation")
        print(f"🤖 AI responding: {ai_text}")
        
        # Safety check: If AI response is empty or very short, regenerate
        if not ai_text or len(ai_text.strip()) < 10:
            print("⚠️ AI response too short, using fallback")
            ai_text = "I'm here to help. Could you tell me more about that?"
        
        # Check if AI wants to transfer
        if "transfer" in ai_text.lower() or "specialist" in ai_text.lower():
            response.say(ai_text, voice=VOICE)
            notify_human_transfer(from_number, call_sid, "AI determined human needed")
            transfer_to_human(response, "Transfer needed")
            return PlainTextResponse(content=str(response), media_type="application/xml")
        
        # Say AI response
        response.say(ai_text, voice=VOICE)
        
        # Continue conversation - wait for their response
        gather = Gather(
            input='speech',
            action='/voice/conversation',
            method='POST',
            speech_timeout='auto',
            timeout=10,
            finish_on_key='#'
        )
        response.append(gather)
        
        # If no response after first gather, prompt them
        response.say("Are you still there?", voice=VOICE)
        
        gather2 = Gather(
            input='speech',
            action='/voice/conversation',
            method='POST',
            timeout=10
        )
        response.append(gather2)
        
        # If STILL no response, try one more time
        response.say("I'm still here. Let me know when you're ready.", voice=VOICE)
        
        gather3 = Gather(
            input='speech',
            action='/voice/conversation',
            method='POST',
            timeout=10
        )
        response.append(gather3)
        
        # Only after ALL 3 gathers timeout (user truly not responding), then transfer
        # NOTE: The below code is added to TwiML but only executes if all gathers timeout
        response.say("I'm having trouble hearing you. Let me connect you with someone who can help.", voice=VOICE)
        
        # Add dial to TwiML (will only execute if all gathers timeout)
        try:
            response.dial(
                number=HUMAN_PHONE,
                timeout=30,
                action='/voice/dial-status',
                method='POST'
            )
        except Exception as e:
            print(f"❌ Error adding dial to response: {e}")
            response.say("Please call us directly at 504-383-3692.", voice=VOICE)
        
    else:
        # No speech detected at all
        print("⚠️ No speech result received")
        response.say("I'm sorry, I didn't hear anything. Let me connect you with a human specialist.", voice=VOICE)
        notify_human_transfer(from_number, call_sid, "No speech detected")
        transfer_to_human(response, "Transfer needed")
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.post("/voice/dial-status")
async def dial_status(request: Request):
    """Track dial status and send notification when transfer connects"""
    form_data = await request.form()
    dial_call_status = form_data.get('DialCallStatus')
    dial_call_duration = form_data.get('DialCallDuration')
    call_sid = form_data.get('CallSid')
    from_number = form_data.get('From')
    
    print(f"📞 Dial Status: {dial_call_status}, Duration: {dial_call_duration}s")
    
    response = VoiceResponse()
    
    if dial_call_status in ['completed', 'answered']:
        # Call was answered and completed - send notification now
        print("✅ Transfer successful!")
        if call_sid and from_number:
            notify_human_transfer(from_number, call_sid, "Transferred after no response to prompts")
        response.say("Thank you for using our service. Goodbye!", voice=VOICE)
    elif dial_call_status == 'busy':
        print("❌ Transfer failed: Line busy")
        response.say("I'm sorry, the line is busy. Please try again later or call us directly at 504-383-3692.", voice=VOICE)
    elif dial_call_status == 'no-answer':
        print("❌ Transfer failed: No answer")
        response.say("I'm sorry, no one answered. Please call us directly at 504-383-3692 or try again later.", voice=VOICE)
    elif dial_call_status == 'failed':
        print("❌ Transfer failed: Call failed")
        response.say("I'm sorry, the transfer failed. Please call us directly at 504-383-3692.", voice=VOICE)
    else:
        print(f"⚠️  Unknown dial status: {dial_call_status}")
        response.say("Thank you for calling.", voice=VOICE)
    
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
        transfer_to_human(response, "Transfer needed")
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
        transfer_to_human(response, "Transfer needed")
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.post("/webhook/payment-confirmed")
async def payment_confirmed_webhook(request: Request):
    """Receive payment confirmation from backend/Stripe"""
    try:
        data = await request.json()
        
        # Expected data: {project_id, user_email, amount, phone_number (optional)}
        project_id = data.get("project_id")
        user_email = data.get("user_email")
        phone_number = data.get("phone_number")
        amount = data.get("amount")
        
        # Prevent duplicate webhook processing (Stripe retries)
        webhook_key = f"payment:{project_id}:{user_email}"
        if webhook_key in sent_integration_forms:
            print(f"⏭️  Skipping duplicate webhook for project {project_id}")
            return {"status": "success", "message": "Already processed"}
        
        print("=" * 70)
        print("💰 PAYMENT CONFIRMED WEBHOOK RECEIVED")
        print("=" * 70)
        print(f"Project ID: {project_id}")
        print(f"Email: {user_email}")
        print(f"Phone: {phone_number}")
        print(f"Amount: ${amount}")
        print("=" * 70)
        
        # Find matching conversation by email or phone
        matched_call_sid = None
        for call_sid, conv in conversations.items():
            conv_email = conv.get("email", "").lower()
            conv_phone = conv.get("phone_number", "")
            
            # Match by email or phone
            if (user_email and conv_email == user_email.lower()) or \
               (phone_number and conv_phone == phone_number):
                matched_call_sid = call_sid
                print(f"✅ Matched to conversation: {call_sid}")
                break
        
        if matched_call_sid:
            # Mark payment as confirmed
            conversations[matched_call_sid]["payment_completed"] = True
            conversations[matched_call_sid]["payment_confirmed_by_webhook"] = True
            conversations[matched_call_sid]["project_id"] = project_id
            
            # Send integration form
            client_email = conversations[matched_call_sid].get("email")
            client_name = conversations[matched_call_sid].get("client_name", "there")
            firm_name = conversations[matched_call_sid].get("firm_name", "your firm")
            
            if client_email:
                send_integration_form_email(client_email, client_name, firm_name)
                print(f"📧 Integration form sent to {client_email}")
            
            return {"status": "success", "message": "Payment confirmed and integration form sent"}
        else:
            print("⚠️  No matching conversation found")
            return {"status": "warning", "message": "Payment received but no active call found"}
            
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.get("/webhook/test")
async def test_webhook():
    """Test endpoint to verify webhook is accessible"""
    return {
        "status": "ok",
        "message": "Webhook endpoint is working",
        "endpoint": "/webhook/payment-confirmed",
        "method": "POST",
        "expected_data": {
            "project_id": "string",
            "user_email": "string",
            "phone_number": "string (optional)",
            "amount": "number"
        }
    }


def send_integration_form_email(client_email: str, client_name: str, firm_name: str):
    """Send integration form link to client after payment"""
    
    # Prevent duplicate integration form emails
    dedup_key = f"{client_email}:{firm_name}"
    if dedup_key in sent_integration_forms:
        print(f"⏭️  Skipping duplicate integration form for {client_email}")
        return
    
    # Mark as sent
    sent_integration_forms.add(dedup_key)
    
    try:
        # Prefer ADMIN_EMAIL (custom domain) over FROM_EMAIL (might be Gmail)
        admin_email = os.getenv("ADMIN_EMAIL")
        from_email = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
        
        # Use custom domain email if available
        sender_email = admin_email if admin_email else from_email
        
        # Check if using Gmail (won't work with Resend)
        if "@gmail.com" in sender_email.lower():
            print("⚠️  WARNING: Gmail detected. Use ADMIN_EMAIL with custom domain instead.")
            print(f"   Set in Railway: ADMIN_EMAIL=noreply@4dgaming.games")
            print(f"   Manual action: Send this link to {client_email}:")
            print(f"   https://4dgaming.games/client-integration.html")
            return
        
        print(f"📧 Sending integration form from: {sender_email}")
        
        params = {
            "from": sender_email,
            "to": [client_email],
            "subject": f"Welcome to 4D Gaming - Integration Form for {firm_name}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px;">
                <h2 style="color: #667eea;">Welcome to 4D Gaming! 🎉</h2>
                
                <p>Hi {client_name},</p>
                
                <p>Thank you for choosing LawBot 360! Your payment has been received and we're excited to get started on your custom AI client intake system.</p>
                
                <div style="background: #e7f3ff; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">📋 Next Step: Complete Your Integration Form</h3>
                    <p>To begin your project, please complete our integration form:</p>
                    <p style="text-align: center; margin: 20px 0;">
                        <a href="https://4dgaming.games/client-integration.html" 
                           style="background: #667eea; color: white; padding: 15px 30px; 
                                  text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                            Complete Integration Form
                        </a>
                    </p>
                    <p style="font-size: 14px;">Or copy this link: https://4dgaming.games/client-integration.html</p>
                </div>
                
                <h3>What Happens Next:</h3>
                <ol>
                    <li>Complete the integration form (takes ~10 minutes)</li>
                    <li>Our team reviews your information within 24 hours</li>
                    <li>You'll receive your project timeline and start date</li>
                    <li>Design and development begins (2 weeks)</li>
                    <li>You get your custom LawBot 360!</li>
                </ol>
                
                <h3>What's Included:</h3>
                <ul>
                    <li>✅ 24/7 AI-powered client intake chatbot</li>
                    <li>✅ Custom conversation flows for your practice areas</li>
                    <li>✅ Lead qualification and consultation scheduling</li>
                    <li>✅ Integration with your existing systems</li>
                    <li>✅ Full training and support</li>
                </ul>
                
                <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Questions?</strong> Reply to this email or call us at (504) 383-3692</p>
                </div>
                
                <p>Thank you for your business!</p>
                
                <p>Best regards,<br/>
                The 4D Gaming Team<br/>
                <a href="https://4dgaming.games">4dgaming.games</a></p>
                
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    This email was sent because you completed payment for LawBot 360 services.
                </p>
            </div>
            """
        }
        
        resend.Emails.send(params)
        print(f"✅ Integration form email sent to {client_email}")
        return True
        
    except Exception as e:
        print(f"⚠️  Failed to send integration form email: {e}")
        print(f"   Manual action: Send this link to {client_email}:")
        print(f"   https://4dgaming.games/client-integration.html")
        return False


def notify_human_transfer(from_number: str, call_sid: str, reason: str):
    """Send email notification with conversation transcript (optional - fails gracefully)"""
    
    # Prevent duplicate notifications for the same call
    if call_sid in sent_notifications:
        print(f"⏭️  Skipping duplicate notification for call {call_sid}")
        return
    
    # Mark this call as notified
    sent_notifications.add(call_sid)
    
    # Get conversation history if available
    conversation_text = "No conversation history available"
    conversation_html = "<p><em>No conversation history available</em></p>"
    
    if call_sid in conversations:
        conv = conversations[call_sid]
        if conv["history"]:
            # Build plain text version
            conversation_text = "\n" + "="*50 + "\nCONVERSATION TRANSCRIPT:\n" + "="*50 + "\n"
            
            # Build HTML version
            conversation_html = "<h3>Conversation Transcript:</h3><div style='background: #f5f5f5; padding: 15px; border-radius: 5px;'>"
            
            for msg in conv["history"]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                
                if role == "user":
                    conversation_text += f"PROSPECT: {content}\n\n"
                    conversation_html += f"<p><strong>Prospect:</strong> {content}</p>"
                elif role == "assistant":
                    conversation_text += f"AI BOT: {content}\n\n"
                    conversation_html += f"<p><strong>AI Bot:</strong> {content}</p>"
            
            conversation_html += "</div>"
            
            # Add context info
            if conv.get("client_name"):
                conversation_text += f"\nClient Name: {conv['client_name']}\n"
                conversation_html += f"<p><strong>Client Name:</strong> {conv['client_name']}</p>"
            if conv.get("firm_name"):
                conversation_text += f"Firm Name: {conv['firm_name']}\n"
                conversation_html += f"<p><strong>Firm Name:</strong> {conv['firm_name']}</p>"
            if conv.get("pain_points"):
                conversation_text += f"Pain Points: {', '.join(conv['pain_points'])}\n"
                conversation_html += f"<p><strong>Pain Points:</strong> {', '.join(conv['pain_points'])}</p>"
    
    # ALWAYS log to console (backup if email fails)
    print("\n" + "="*70)
    print("🔔 LIVE CALL TRANSFER")
    print("="*70)
    print(f"From: {from_number}")
    print(f"Reason: {reason}")
    print(f"Call SID: {call_sid}")
    print(f"Transferring to: {HUMAN_PHONE}")
    print(conversation_text)
    print("="*70 + "\n")
    
    # Try to send email (but don't crash if it fails)
    try:
        # Prefer ADMIN_EMAIL (custom domain) for sending
        admin_email = os.getenv("ADMIN_EMAIL")
        from_email = os.getenv("FROM_EMAIL")
        
        # DEBUG: Log what we got from environment
        print(f"🔍 DEBUG - ADMIN_EMAIL from env: {admin_email}")
        print(f"🔍 DEBUG - FROM_EMAIL from env: {from_email}")
        
        # Use custom domain for sending
        sender_email = admin_email if admin_email else from_email
        
        # Send notification to FROM_EMAIL (your personal email)
        recipient_email = from_email if from_email else "onboarding@resend.dev"
        
        print(f"🔍 DEBUG - Will send from: {sender_email}")
        print(f"🔍 DEBUG - Will send to: {recipient_email}")
        
        if not sender_email:
            print("⚠️  No ADMIN_EMAIL or FROM_EMAIL set. Email not sent.")
            print("   Set in Railway: ADMIN_EMAIL=noreply@4dgaming.games")
            return
        
        # Check if using Gmail for sender (won't work with Resend)
        if "@gmail.com" in sender_email.lower():
            print("⚠️  WARNING: Gmail detected for sending. Use ADMIN_EMAIL with custom domain.")
            print("   Set in Railway: ADMIN_EMAIL=noreply@4dgaming.games")
            print("   Transcript logged above ↑")
            return
        
        print(f"📧 Sending notification from: {sender_email} to: {recipient_email}")
        
        params = {
            "from": sender_email,
            "to": [recipient_email],
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
        print(f"✅ Email sent successfully to {from_email}")
        
    except Exception as e:
        print(f"⚠️  Email notification failed (non-critical): {e}")
        print("   Transcript is logged above - you can still see the conversation!")
        print("   To enable emails: Use a verified domain email (not Gmail)")
        print("   Or verify your domain at: https://resend.com/domains")


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