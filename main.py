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
            "phase": "SALES",  # Start in SALES phase
            "current_step": 0,
            "committed": False,  # Track if they've committed to buy
            "client_name": None,
            "firm_name": None,
            "email": None,
            "selected_addons": [],
            "selected_maintenance": None,
            "payment_completed": False
        }
    
    conv = conversations[call_sid]
    conv["history"].append({"role": "user", "content": user_input})
    
    # Detect if they've committed to buying
    user_input_lower = user_input.lower()
    commitment_phrases = ['yes', 'let\'s do it', 'i\'m ready', 'sign me up', 'let\'s get started', 'i want it', 'sounds good', 'okay', 'sure']
    
    # Check if we should switch from SALES to ONBOARDING phase
    if conv["phase"] == "SALES" and any(phrase in user_input_lower for phrase in commitment_phrases):
        # Look at conversation context - if we've pitched and they're agreeing, they're committed
        recent_history = ' '.join([msg.get('content', '') for msg in conv["history"][-3:]])
        if any(word in recent_history.lower() for word in ['start', 'get you set up', 'ready to begin', 'make sense']):
            conv["committed"] = True
            conv["phase"] = "ONBOARDING"
            print("🎯 SALES CLOSED! Switching to ONBOARDING mode")
    
    # Build system prompt based on phase
    if conv["phase"] == "SALES":
        system_prompt = f"""You are an AGGRESSIVE, CONFIDENT sales closer for LawBot 360.

Current stage: {stage}
Client name: {conv.get('client_name', 'Unknown')}
Firm: {conv.get('firm_name', 'Unknown')}
Phase: SALES MODE

YOUR GOAL: CLOSE THE SALE RIGHT NOW - Get them to commit to buying TODAY

CRITICAL SALES RULES:
1. Be AGGRESSIVE but not rude - you're confident because your product is amazing
2. Keep responses SHORT (1-2 sentences) - this is a phone call
3. Create URGENCY - they need this NOW
4. ASSUME THE SALE - act like they're already buying
5. Handle objections FAST and keep pushing forward
6. ASK FOR THE SALE directly and repeatedly
7. Don't let them delay or "think about it"

PRODUCT: LawBot 360
- 24/7 AI client intake - captures leads while you sleep
- 40% more clients on average
- $25,000 base (but pays for itself in 2-3 cases)
- $7,500 down payment gets them started TODAY
- Setup in 2-3 weeks

AGGRESSIVE SALES APPROACH:
1. Opening: "Are you losing leads after hours? Of course you are - everyone does."
2. Pain: "How many potential clients call and hang up because nobody answers?"
3. Solution: "LawBot captures those leads 24/7. 40% more clients."
4. ROI: "If you land just 2-3 more cases per month, it pays for itself. That's conservative."
5. TRIAL CLOSE: "Does that make sense for your practice?"
6. When they show ANY interest → CLOSE HARD: "Perfect! Let's get you set up right now."
7. ASSUME SALE: "Here's what we're going to do..."
8. Switch to ONBOARDING mode

DO NOT in SALES mode:
- ❌ Be timid or uncertain
- ❌ Give them time to think
- ❌ Offer to call back later
- ❌ Let them delay
- ❌ Accept "I need to think about it" (handle the objection!)

OBJECTION HANDLING:
- "Too expensive" → "It pays for itself in 2-3 cases. You're losing money NOT having it."
- "Need to think" → "What specifically do you need to think about? Let's address it now."
- "Need to discuss with partner" → "That's fine - let's get you set up and you can coordinate internally."
- "Not right now" → "Every day you wait is leads you're losing. Let's at least get you in the system."

Remember: Be AGGRESSIVE, CONFIDENT, ASSUMPTIVE. Close the sale NOW!
"""
    
    else:  # ONBOARDING phase
        system_prompt = f"""You are a patient, helpful onboarding specialist for 4D Gaming.

Current stage: {stage}
Current step: {conv.get('current_step', 0)}/14
Client name: {conv.get('client_name', 'Unknown')}
Firm: {conv.get('firm_name', 'Unknown')}
Phase: ONBOARDING MODE (Sale is closed!)

YOUR GOAL: Walk them through COMPLETE setup - from portal login to payment completion

ONBOARDING RULES:
1. Be PATIENT and FRIENDLY - you're helping them through a process
2. ONE step at a time - wait for confirmation before moving forward
3. Keep responses SHORT (1-2 sentences)
4. Answer questions about features thoroughly
5. Never rush - this is their money, let them take their time
6. Guide them gently through each step

ONBOARDING STEPS (in order):

STEP 1: "Perfect! Let's get you set up right now. Open your browser and go to 4dgaming.games/client-portal.html. Tell me when you have it open."

STEP 2: "Great! Now create your account or log in. Let me know when you're in."

STEP 3: "Excellent! Scroll down and click 'Start a new project'. See it?"

STEP 4: "Perfect! Click the dropdown for 'Select service', scroll down, and choose 'LawBot 360'. Done?"

STEP 5: "Great! Where it says 'Project name', type in your firm's name. What's the firm name?"

STEP 6: "Good! Fill in 'Brief description' - just describe what you need. Then 'Project details'. Ready to continue?"

STEP 7: "Now you'll see Optional Features - add-ons like iOS/Android apps ($5,000), Multi-language ($1,500), Advanced Analytics ($2,000), SMS/WhatsApp ($1,000), or Multi-location support ($3,000). Want any add-ons?"

STEP 8: "Perfect! Choose a Monthly Maintenance Plan: Basic ($497/month - hosting, security, support), Professional ($997/month - everything + priority support), Premium ($1,997/month - everything + 24/7 support), or No Maintenance Plan. Which one?"

STEP 9: "Excellent! Click 'Create Project'. Tell me when it's created."

STEP 10: "Great! Look at the right side for your project summary. See it?"

STEP 11: "Perfect! Want to upload any files or add a message? If not, we can skip to payment."

STEP 12: "Excellent! You'll see 'Fund Milestone 1' button with your total. Click it - you'll go to Stripe. Tell me when you're on the payment page."

STEP 13: "Take your time with payment. I'm right here. Let me know when it's done."

STEP 14: "Congratulations! Payment complete! Here's what's next:
- Our team reviews within 24 hours
- You get timeline and start date
- Setup takes 2-3 weeks
I'm sending the integration form to your email: 4dgaming.games/client-integration.html
Any questions about your new LawBot 360?"

Remember: Be PATIENT, HELPFUL, ONE STEP AT A TIME. They already bought - now help them complete the purchase!
"""
    
    # Get AI response
    messages = [
        {"role": "system", "content": system_prompt}
    ] + conv["history"][-15:]  # Last 15 messages
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            temperature=0.7 if conv["phase"] == "SALES" else 0.6,
            max_tokens=100 if conv["phase"] == "SALES" else 120
        )
        
        ai_response = response.choices[0].message.content
        conv["history"].append({"role": "assistant", "content": ai_response})
        
        # Track onboarding step progression
        if conv["phase"] == "ONBOARDING":
            response_lower = ai_response.lower()
            if "4dgaming.games/client-portal" in response_lower:
                conv["current_step"] = 1
            elif "log in" in response_lower or "create your account" in response_lower:
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
            elif "create project" in response_lower and "click" in response_lower:
                conv["current_step"] = 9
            elif "project summary" in response_lower:
                conv["current_step"] = 10
            elif "upload" in response_lower or "files" in response_lower:
                conv["current_step"] = 11
            elif "fund milestone" in response_lower or "stripe" in response_lower:
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
        
        # Check if user confirmed payment completion
        payment_keywords = ['payment complete', 'payment is done', 'paid', 'payment went through', 'transaction complete', 'payment successful']
        if any(keyword in speech_result.lower() for keyword in payment_keywords):
            if call_sid in conversations:
                conv = conversations[call_sid]
                conv["payment_completed"] = True
                
                # Try to send integration form email
                client_email = conv.get("email")
                client_name = conv.get("client_name", "there")
                firm_name = conv.get("firm_name", "your firm")
                
                if client_email:
                    send_integration_form_email(client_email, client_name, firm_name)
                    print(f"📧 Integration form email sent to {client_email}")
                else:
                    print("⚠️  No email address collected - cannot send integration form")
        
        # Check if user provided email address
        if "@" in speech_result and "." in speech_result:
            # Extract email from speech (rough extraction)
            words = speech_result.lower().split()
            for word in words:
                if "@" in word and "." in word:
                    if call_sid in conversations:
                        conversations[call_sid]["email"] = word.strip(".,!?")
                        print(f"📧 Email captured: {word}")
        
        # Check if user provided firm name
        if "firm" in speech_result.lower() or "law" in speech_result.lower():
            if call_sid in conversations:
                # Try to extract firm name (this is rough - might need refinement)
                conversations[call_sid]["firm_name"] = speech_result
        
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
        
        # Check if onboarding is complete (payment done and questions asked)
        if call_sid in conversations:
            conv = conversations[call_sid]
            if conv.get("payment_completed") and "any questions" in ai_text.lower():
                # This might be the end of the call - prepare for potential goodbye
                print("✅ Onboarding complete - waiting for final questions or goodbye")
        
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


def send_integration_form_email(client_email: str, client_name: str, firm_name: str):
    """Send integration form link to client after payment"""
    try:
        from_email = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
        
        # Check if using Gmail
        if "@gmail.com" in from_email.lower():
            print("⚠️  WARNING: Using Gmail address. Email not sent.")
            print(f"   Manual action: Send this link to {client_email}:")
            print(f"   https://4dgaming.games/client-integration.html")
            return
        
        params = {
            "from": from_email,
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
                    <li>Design and development begins (2-3 weeks)</li>
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
        from_email = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
        
        # Check if using Gmail (which requires verification)
        if "@gmail.com" in from_email.lower():
            print("⚠️  WARNING: Using Gmail address. Resend requires verified domains.")
            print("   To fix: Use a custom domain email or verify Gmail in Resend.")
            print("   Transcript logged above ↑")
            return  # Skip email, but continue (don't crash)
        
        params = {
            "from": from_email,
            "to": [from_email],
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