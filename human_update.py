"""
LawBot 360 Voice Sales Agent - Updated Version
- AI disclosure upfront
- Human handoff option
- Resend email integration
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime

# AI & Voice
from openai import OpenAI
from TTS.api import TTS
import speech_recognition as sr

# Communications
import resend
from twilio.rest import Client as TwilioClient

# Payment
import stripe


class ConversationStage(Enum):
    """Sales conversation stages"""
    GREETING = "greeting"
    DISCOVERY = "discovery"
    PAIN_POINTS = "pain_points"
    SOLUTION_PRESENTATION = "solution_presentation"
    FEATURES_EXPLANATION = "features_explanation"
    PRICING_DISCUSSION = "pricing_discussion"
    ADDONS_PRESENTATION = "addons_presentation"
    MAINTENANCE_PLANS = "maintenance_plans"
    OBJECTION_HANDLING = "objection_handling"
    CLOSING = "closing"
    HUMAN_HANDOFF = "human_handoff"  # NEW: Transfer to human
    PORTAL_SIGNUP = "portal_signup"
    PAYMENT_SETUP = "payment_setup"
    NEXT_STEPS = "next_steps"
    INTEGRATION_FORM = "integration_form"
    COMPLETED = "completed"


@dataclass
class ConversationContext:
    """Maintains conversation state and memory"""
    
    # Client Information
    client_name: Optional[str] = None
    firm_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    
    # Conversation tracking
    current_stage: ConversationStage = ConversationStage.GREETING
    conversation_history: List[Dict] = field(default_factory=list)
    
    # Discovery information
    pain_points: List[str] = field(default_factory=list)
    current_intake_method: Optional[str] = None
    monthly_inquiries: Optional[str] = None
    
    # Product interest
    interested_addons: List[str] = field(default_factory=list)
    selected_maintenance_plan: Optional[str] = None
    
    # Pricing
    base_price: float = 25000.00
    total_price: float = 25000.00
    
    # Status tracking
    objections_raised: List[str] = field(default_factory=list)
    questions_asked: List[str] = field(default_factory=list)
    off_topic_count: int = 0
    wants_human: bool = False  # NEW: Track if they want human
    
    # Deal status
    deal_closed: bool = False
    payment_completed: bool = False
    integration_form_sent: bool = False
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "stage": self.current_stage.value
        })
    
    def to_dict(self) -> dict:
        """Convert to dictionary for saving"""
        return {
            "client_name": self.client_name,
            "firm_name": self.firm_name,
            "email": self.email,
            "phone": self.phone,
            "current_stage": self.current_stage.value,
            "conversation_history": self.conversation_history,
            "pain_points": self.pain_points,
            "interested_addons": self.interested_addons,
            "selected_maintenance_plan": self.selected_maintenance_plan,
            "total_price": self.total_price,
            "deal_closed": self.deal_closed,
            "payment_completed": self.payment_completed,
            "integration_form_sent": self.integration_form_sent,
            "wants_human": self.wants_human
        }


class VoiceSalesBot:
    """Main voice sales bot with AI conversation and voice capabilities"""
    
    def __init__(self):
        # Initialize OpenAI
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4-turbo-preview"
        
        # Initialize Resend for emails
        resend.api_key = os.getenv("RESEND_API_KEY")
        
        # Initialize Twilio for transfers
        self.twilio_client = TwilioClient(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        self.human_phone = os.getenv("PHONE")  # Your phone number
        
        # Initialize TTS with cloned voice
        print("Loading voice clone...")
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
        self.reference_voice = "reference_voice.wav"
        
        # Initialize Speech Recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Initialize Stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        
        # Conversation context
        self.context = ConversationContext()
        
        # Product knowledge base
        self.load_product_knowledge()
    
    def load_product_knowledge(self):
        """Load LawBot 360 product information"""
        
        self.product_info = {
            "base_features": [
                "24/7 AI-powered chatbot for client intake",
                "Full AI intake system for all your practice areas",
                "Custom conversation scripts for Personal Injury, Family Law, Immigration, Criminal, Estate, etc.",
                "Document upload & attachment to the case file",
                "Automated follow-up messages",
                "Consultation scheduling",
                "Optional Salesforce / Clio / MyCase integration",
                "Email and SMS notifications"
            ],
            
            "addons": {
                "Native iOS & Android mobile apps": {
                    "price": 5000,
                    "description": "Native iOS and Android apps utilizing the latest technologies"
                },
                "Multi-language support": {
                    "price": 1500,
                    "description": "Multi-language support to meet all your client needs"
                },
                "Advanced Analytics": {
                    "price": 500,
                    "description": "Detailed insights on lead quality, conversion rates, and ROI"
                },
                "SMS/WhatsApp integration": {
                    "price": 1000,
                    "description": "Connect to SMS/WhatsApp to stay connected"
                },
                "Multi-location support": {
                    "price": 3000,
                    "description": "Multi-location support keeps all locations connected"
                }
            },
            
            "maintenance_plans": {
                "Basic Maintenance": {
                    "monthly": 497,
                    "includes": [
                        "Server hosting & monitoring (99.9% uptime)",
                        "Security patches & updates",
                        "Bug fixes",
                        "Email support (48hr response)",
                        "Monthly performance reports",
                        "Database backups (weekly)"
                    ]
                },
                "Professional Maintenance": {
                    "monthly": 997,
                    "includes": [
                        "Everything in Basic, PLUS:",
                        "Priority support (24hr response)",
                        "Phone support during business hours",
                        "Monthly optimization calls & improvements",
                        "Database backups (daily)",
                        "Minor content updates (up to 2 hours/month)"
                    ]
                },
                "Enterprise Maintenance": {
                    "monthly": 1997,
                    "includes": [
                        "Everything in Professional, PLUS:",
                        "Dedicated account manager",
                        "Priority support (4-hour response)",
                        "24/7 emergency phone support",
                        "Weekly performance reviews",
                        "Advanced analytics & insights",
                        "Up to 10 hours/month development time",
                        "Custom feature requests prioritized"
                    ]
                },
                "No Maintenance Plan": {
                    "monthly": 0,
                    "includes": [
                        "Self-managed (not recommended)",
                        "You handle all updates and fixes yourself"
                    ]
                }
            },
            
            "payment_structure": {
                "milestone_1": {
                    "name": "Project Kickoff",
                    "percentage": 30,
                    "deliverables": "Initial setup, design mockups, and project planning"
                },
                "milestone_2": {
                    "name": "Development",
                    "percentage": 50,
                    "deliverables": "Core development, integrations, and testing"
                },
                "milestone_3": {
                    "name": "Launch",
                    "percentage": 20,
                    "deliverables": "Final deployment, training, and handoff"
                }
            }
        }
    
    def get_sales_script_context(self) -> str:
        """Get current stage script and context for AI"""
        
        stage_scripts = {
            ConversationStage.GREETING: """
You are an AI sales assistant for 4D Gaming, calling to discuss LawBot 360.

CRITICAL: DISCLOSE YOU'RE AN AI IMMEDIATELY

OPENING SCRIPT:
"Hi! This is an AI sales assistant calling from 4D Gaming about LawBot 360, our AI-powered 
client intake system for law firms. Quick question - are you losing leads outside business hours? 

I can walk you through how we solve that, or if you prefer, I can connect you with a human 
team member right away. Which would you prefer?"

GOAL: Get their preference (talk to AI or human) and get their name

IF THEY WANT HUMAN:
→ Move to HUMAN_HANDOFF stage immediately

IF THEY'LL TALK TO AI:
"Great! Who am I speaking with?"

REMEMBER: Full transparency that you're an AI. Offer human handoff upfront.
""",
            
            ConversationStage.DISCOVERY: """
GOAL: Quickly identify 1-2 pain points (2 minutes max)

ALWAYS REMIND: "At any point, if you'd prefer to speak with a human, just let me know and I'll transfer you immediately."

ASK ONLY THESE:
1. "How do you handle leads that come in after 5pm or on weekends?"
2. "What happens when your receptionist is out sick or on vacation?"

LISTEN FOR:
- "We miss them" = PAIN POINT
- "They wait until next day" = PAIN POINT  
- "Partner answers phone" = PAIN POINT

AS SOON AS you hear a pain point, IMMEDIATELY transition to solution:
"That's exactly what LawBot 360 solves. Let me show you how..."

IF THEY ASK FOR HUMAN: → Move to HUMAN_HANDOFF stage

DO NOT:
- Ask 10 discovery questions
- Do deep needs analysis
- Schedule follow-up discovery call
""",
            
            ConversationStage.SOLUTION_PRESENTATION: """
GOAL: Quick pitch (1 minute) then GO TO PRICING

REMINDER: "If you'd like more detail or want to speak with a human specialist, just say so."

PITCH:
"LawBot 360 is your complete AI intake system. Works 24/7 across all your practice areas - 
Personal Injury, Family Law, Criminal, Immigration, Estate - with custom scripts for each.
Uploads documents, schedules consults, integrates with Clio/Salesforce, sends follow-ups.

Most firms sign up 5-10 new clients per month just from after-hours leads they were missing.
That's $500k to $1M per year in captured revenue."

THEN IMMEDIATELY:
"The investment is $25,000 one-time for the complete system. Most firms see full ROI 
in 30-60 days from just 2-3 extra cases. $7,500 to start today.

Does that work, or would you like me to connect you with a human to discuss details?"

IF THEY WANT HUMAN: → Move to HUMAN_HANDOFF
""",
            
            ConversationStage.PRICING_DISCUSSION: """
GOAL: State price confidently and CLOSE or HANDOFF

PRICE STATEMENT:
"$25,000 one-time for the complete system. That includes everything - custom scripts for all 
your practice areas, integrations, training, the works.

You pay 30% now to start ($7,500), 50% when we're building it ($12,500), 20% when we launch ($5,000)."

THEN TRIAL CLOSE:
"Does that work for you, or would you like to discuss with a human team member?"

IF THEY HESITATE:
"I totally understand - $25,000 is a serious investment. Would you like me to transfer you to 
a human specialist who can walk through the ROI and answer specific questions? Or I can continue?"

IF PRICE OBJECTION:
"Let me connect you with our sales specialist who can discuss financing options and ROI calculations. 
Sound good?"

REMEMBER: At this price point, OFFER human handoff proactively.
""",
            
            ConversationStage.HUMAN_HANDOFF: """
GOAL: Transfer to human or schedule callback

YOU HAVE TWO OPTIONS:

OPTION 1: IMMEDIATE TRANSFER
"Perfect! I'm transferring you to a human specialist right now. Please hold for just a moment."
→ Use Twilio transfer to {human_phone}

OPTION 2: SCHEDULE CALLBACK
"I can have a human specialist call you back. What's the best number to reach you, and what 
time works best - today, tomorrow, or this week?"
→ Get their phone number
→ Get preferred callback time
→ Send email notification to team

CONFIRM:
"Got it! [Human name] will call you at [phone] [timeframe]. You'll also receive a confirmation 
email. Anything else I can help with right now?"
""",
            
            ConversationStage.ADDONS_PRESENTATION: """
GOAL: Quick upsell (30 seconds max), then move to close

REMINDER: "Want a human to walk through all the options? I can transfer you."

ONLY IF they seem very interested:
"Quick question - do you also need native mobile apps? iOS and Android for $5,000. 
Or if you have multiple locations, multi-location support for $3,000.

Want details on any of those, or should I transfer you to discuss add-ons with a specialist?"

IF YES: Add to price, then CLOSE
IF WANT HUMAN: → Move to HUMAN_HANDOFF
IF NO: "No problem. Base system it is."
""",
            
            ConversationStage.MAINTENANCE_PLANS: """
GOAL: Mention it exists, offer human for details

"One more thing - ongoing maintenance. Most firms choose Basic at $497/month for hosting, 
updates, and support. Or self-manage at no cost.

Want me to connect you with someone to explain the different tiers, or are you good with Basic?"

IF WANT DETAILS: → Move to HUMAN_HANDOFF
IF GOOD: "Awesome. Let's get you set up."
""",
            
            ConversationStage.CLOSING: """
GOAL: Close the sale or handoff to human

ASSUMPTIVE CLOSE:
"Alright [Name], let's get you set up. What's your email?"

IF THEY HESITATE:
"Totally understand if you'd like to speak with a human before committing. Should I transfer 
you to our sales team, or would you like to continue with me?"

IF WANT HUMAN: → Move to HUMAN_HANDOFF

IF CONTINUE:
"Great! I'll send you the portal link. $7,500 to start and you're live in 6 weeks."

REMEMBER: At $25k, many will want human verification. That's normal and expected.
""",
            
            ConversationStage.PORTAL_SIGNUP: """
GOAL: Get them into portal or transfer to human for help

"Perfect! I'm sending you the portal link to {email} right now.

If you need help with the payment process or have questions, I can transfer you to our 
onboarding specialist. Or I can stay on the line and guide you through. What works better?"

IF WANT HUMAN: → Move to HUMAN_HANDOFF
IF WANT AI HELP: "Great, check your email - got it? Click that link..."
""",
            
            ConversationStage.PAYMENT_SETUP: """
GOAL: Get payment processed or transfer for assistance

"You should see the payment page for $7,500.

If you have any questions about payment security, milestones, or need to discuss payment 
options, I can connect you with our finance team right now. Or just enter your card and we're done."

IF WANT HUMAN: → Move to HUMAN_HANDOFF
IF CONTINUE: "Go ahead and enter that card info."
""",
            
            ConversationStage.INTEGRATION_FORM: """
GOAL: Send form, offer human help

"Perfect! I'm sending the integration form to {email} now. This collects your tech requirements.

Our implementation team will reach out within 48 hours to schedule your kickoff call. They'll 
walk you through everything.

Want me to have someone call you today to explain the process, or are you all set?"

IF WANT CALL: → Move to HUMAN_HANDOFF
IF ALL SET: → Move to COMPLETED
""",
            
            ConversationStage.NEXT_STEPS: """
GOAL: Set expectations, offer human contact

"You're all set! Here's what happens next:
1. Implementation team calls you within 48 hours
2. 6-week development timeline
3. You'll track everything in the portal

Want me to have someone call you today to introduce themselves, or you're good to go?"

IF WANT CALL: → Move to HUMAN_HANDOFF
IF GOOD: → Move to COMPLETED
""",
            
            ConversationStage.COMPLETED: """
GOAL: Warm close with human contact option

"[Name], thanks for choosing 4D Gaming and LawBot 360! 

If you have any questions before your kickoff call, you can reply to the confirmation email 
or call our office at {office_phone}. We're here to help.

Looking forward to helping you capture more leads!"
"""
        }
        
        return stage_scripts.get(self.context.current_stage, "Continue the conversation professionally. Offer human handoff if needed.")
    
    def create_system_prompt(self) -> str:
        """Create comprehensive system prompt for OpenAI"""
        
        milestone_1 = self.context.total_price * 0.30
        milestone_2 = self.context.total_price * 0.50
        milestone_3 = self.context.total_price * 0.20
        
        return f"""You are an AI sales assistant for 4D Gaming, selling LawBot 360.

CRITICAL RULES:
1. ALWAYS disclose you're an AI assistant upfront
2. ALWAYS offer human handoff option at ANY point
3. If they want to speak to a human, IMMEDIATELY move to HUMAN_HANDOFF stage
4. Be transparent, helpful, and don't try to "trick" them into staying with AI

CURRENT CONVERSATION STAGE: {self.context.current_stage.value}

CLIENT CONTEXT:
- Name: {self.context.client_name or "Not captured yet"}
- Firm: {self.context.firm_name or "Not captured"}
- Email: {self.context.email or "NEED THIS TO CLOSE"}
- Phone: {self.context.phone or "Not captured"}
- Wants Human: {self.context.wants_human}
- Pain Points: {', '.join(self.context.pain_points) if self.context.pain_points else "None yet"}
- Stage: {self.context.current_stage.value}
- Total Price: ${self.context.total_price:,.2f}
- First Payment: ${milestone_1:,.2f}

STAGE GUIDANCE:
{self.get_sales_script_context()}

PRODUCT KNOWLEDGE:
Base Price: $25,000 (one-time)
First milestone: ${milestone_1:,.2f} (30% to start TODAY)
Second milestone: ${milestone_2:,.2f} (50% during dev)
Final milestone: ${milestone_3:,.2f} (20% at launch)

HUMAN HANDOFF TRIGGERS:
Listen for these phrases and IMMEDIATELY offer human transfer:
- "speak to a person"
- "talk to someone"
- "human"
- "real person"
- "representative"
- "too complicated"
- "need to discuss"
- "have questions"
- Any frustration or confusion

When you detect these, say:
"I can transfer you to a human specialist right now. Would you like that?"

SALES RULES:
1. MOVE FAST: Get name → Find pain → Pitch → Quote price → Close or Handoff
2. BE TRANSPARENT: You're an AI, be upfront about it
3. OFFER HUMAN HELP: At every major decision point, offer human transfer
4. STAY HELPFUL: If they prefer AI, great. If they want human, great. Either way is fine.

OUTPUT FORMAT:
- Keep responses SHORT (1-2 sentences max)
- Sound natural and helpful
- ALWAYS remind them human handoff is available
- If they want human, confirm and move to HUMAN_HANDOFF stage

Remember: You're a helpful AI assistant. Your job is to help them get the information they 
need - whether that's from you or from a human. Don't be pushy about staying with AI."""
    
    def chat_with_gpt(self, user_message: str) -> str:
        """Get AI response from OpenAI"""
        
        # Add user message to history
        self.context.add_message("user", user_message)
        
        # Check if they want human
        user_lower = user_message.lower()
        human_triggers = ["speak to a person", "talk to someone", "human", "real person", 
                         "representative", "actual person", "transfer me", "speak to human"]
        
        if any(trigger in user_lower for trigger in human_triggers):
            self.context.wants_human = True
            self.context.current_stage = ConversationStage.HUMAN_HANDOFF
        
        # Build messages for OpenAI
        messages = [
            {"role": "system", "content": self.create_system_prompt()}
        ]
        
        # Add conversation history (last 10 messages)
        recent_history = self.context.conversation_history[-10:]
        for msg in recent_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Get response from OpenAI
        try:
            response = self.openai.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message.content
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            assistant_message = "I apologize, I'm having a technical issue. Let me transfer you to a human who can help."
            self.context.wants_human = True
            self.context.current_stage = ConversationStage.HUMAN_HANDOFF
        
        # Add assistant response to history
        self.context.add_message("assistant", assistant_message)
        
        # Extract information
        self.extract_info_from_response(user_message, assistant_message)
        
        # Check if should advance stage
        self.maybe_advance_stage(assistant_message)
        
        return assistant_message
    
    def extract_info_from_response(self, user_message: str, assistant_message: str):
        """Extract client information from conversation"""
        
        user_lower = user_message.lower()
        
        # Extract email
        if "@" in user_message and not self.context.email:
            import re
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', user_message)
            if email_match:
                self.context.email = email_match.group()
        
        # Extract phone
        if not self.context.phone:
            import re
            phone_match = re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', user_message)
            if phone_match:
                self.context.phone = phone_match.group()
    
    def maybe_advance_stage(self, assistant_message: str):
        """Determine if conversation should advance to next stage"""
        
        message_lower = assistant_message.lower()
        
        # Don't auto-advance if in human handoff
        if self.context.current_stage == ConversationStage.HUMAN_HANDOFF:
            return
        
        # Stage advancement logic
        stage_transitions = {
            ConversationStage.GREETING: {
                "next": ConversationStage.DISCOVERY,
                "triggers": ["who am i speaking", "your name", "tell me about"]
            },
            ConversationStage.DISCOVERY: {
                "next": ConversationStage.SOLUTION_PRESENTATION,
                "triggers": ["lawbot 360", "let me show", "solve that"]
            },
            ConversationStage.SOLUTION_PRESENTATION: {
                "next": ConversationStage.PRICING_DISCUSSION,
                "triggers": ["investment is", "25,000", "$25"]
            },
            ConversationStage.PRICING_DISCUSSION: {
                "next": ConversationStage.CLOSING,
                "triggers": ["does that work", "let's get you set"]
            }
        }
        
        current_transition = stage_transitions.get(self.context.current_stage)
        if current_transition:
            triggers = current_transition["triggers"]
            if any(trigger in message_lower for trigger in triggers):
                self.context.current_stage = current_transition["next"]
                print(f"\n[STAGE ADVANCED: {self.context.current_stage.value}]\n")
    
    def transfer_to_human(self, call_sid: str = None):
        """Transfer call to human using Twilio"""
        
        if not call_sid:
            print("⚠️  No call SID - can't transfer (text mode)")
            return False
        
        try:
            # Transfer the call to human phone
            self.twilio_client.calls(call_sid).update(
                twiml=f'<Response><Dial>{self.human_phone}</Dial></Response>'
            )
            print(f"✅ Transferred call to {self.human_phone}")
            return True
        except Exception as e:
            print(f"❌ Transfer error: {e}")
            return False
    
    def schedule_callback(self, name: str, phone: str, email: str, preferred_time: str):
        """Schedule callback and notify team via email"""
        
        try:
            # Send email to team using Resend
            params = {
                "from": os.getenv("FROM_EMAIL", "onboarding@resend.dev"),
                "to": [os.getenv("FROM_EMAIL")],  # Your email
                "subject": f"🔔 Callback Request: {name} - LawBot 360",
                "html": f"""
                <h2>New Callback Request</h2>
                
                <p><strong>Client:</strong> {name}</p>
                <p><strong>Phone:</strong> {phone}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Preferred Time:</strong> {preferred_time}</p>
                
                <h3>Context:</h3>
                <p>Client was speaking with AI assistant about LawBot 360 ($25,000 base package) 
                and requested human follow-up.</p>
                
                <p><strong>Call them at:</strong> {phone}</p>
                """
            }
            
            resend.Emails.send(params)
            print(f"✅ Callback notification sent for {name}")
            return True
            
        except Exception as e:
            print(f"❌ Callback email error: {e}")
            return False
    
    def send_integration_form(self, email: str, client_name: str, firm_name: str):
        """Send integration form to client using Resend"""
        
        integration_form_url = os.getenv("INTEGRATION_FORM_URL", "https://yourdomain.com/client-integration-form.html")
        
        try:
            params = {
                "from": os.getenv("FROM_EMAIL", "onboarding@resend.dev"),
                "to": [email],
                "subject": f"LawBot 360 System Integration Form - {firm_name}",
                "html": f"""
                <html>
                    <body>
                        <h2>Welcome to LawBot 360, {client_name}!</h2>
                        
                        <p>Thank you for choosing 4D Gaming for your AI-powered client intake solution.</p>
                        
                        <p>To begin your project, please complete our System Integration Form:</p>
                        
                        <p style="margin: 30px 0;">
                            <a href="{integration_form_url}" 
                               style="background: #667eea; color: white; padding: 15px 30px; 
                                      text-decoration: none; border-radius: 5px; font-weight: bold;">
                                Complete Integration Form
                            </a>
                        </p>
                        
                        <p>This form collects technical details about your:</p>
                        <ul>
                            <li>Current website and hosting</li>
                            <li>Existing systems and integrations</li>
                            <li>Business requirements</li>
                            <li>Technical contacts</li>
                        </ul>
                        
                        <p>The form takes about 10 minutes to complete.</p>
                        
                        <h3>What Happens Next</h3>
                        <p>1. Complete the integration form<br/>
                           2. Our team reviews your information within 48 hours<br/>
                           3. We'll schedule your project kickoff call<br/>
                           4. Design and development begins!</p>
                        
                        <p>Questions? Reply to this email or call us at {os.getenv('PHONE', '(555) 123-4567')}</p>
                        
                        <p>Best regards,<br/>
                        The 4D Gaming Team</p>
                    </body>
                </html>
                """
            }
            
            resend.Emails.send(params)
            print(f"✅ Integration form sent to {email}")
            self.context.integration_form_sent = True
            return True
            
        except Exception as e:
            print(f"❌ Email send error: {e}")
            return False
    
    def save_conversation(self):
        """Save conversation to file"""
        
        filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.context.to_dict(), f, indent=2)
        
        print(f"💾 Conversation saved: {filename}")
    
    def run_text_conversation(self):
        """Run conversation in text mode"""
        
        print("\n" + "="*70)
        print("🤖 LawBot 360 AI Sales Assistant (OpenAI - Text Mode)")
        print("="*70)
        print("Type your responses. Type 'quit' to exit.\n")
        
        # Opening message with AI disclosure
        opening = """Hi! This is an AI sales assistant calling from 4D Gaming about LawBot 360, 
our AI-powered client intake system for law firms. 

Quick question - are you losing leads outside business hours? 

I can walk you through how we solve that, or if you prefer, I can have a human 
team member call you instead. Which would you prefer?"""
        
        print(f"🤖 AI Assistant: {opening}\n")
        
        # Conversation loop
        while self.context.current_stage != ConversationStage.COMPLETED:
            # Get user input
            user_input = input("👤 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("Ending conversation...")
                break
            
            # Get AI response
            bot_response = self.chat_with_gpt(user_input)
            
            print(f"\n🤖 AI Assistant: {bot_response}\n")
            
            # Handle human handoff
            if self.context.current_stage == ConversationStage.HUMAN_HANDOFF:
                if self.context.phone and self.context.email:
                    # Schedule callback
                    preferred_time = input("👤 Preferred callback time: ").strip()
                    self.schedule_callback(
                        self.context.client_name or "Prospect",
                        self.context.phone,
                        self.context.email,
                        preferred_time
                    )
                    print("\n✅ Callback scheduled! Human will reach out soon.\n")
                    break
                else:
                    print("\n[System: In phone mode, this would transfer to human immediately]\n")
            
            # Handle integration form
            if self.context.current_stage == ConversationStage.INTEGRATION_FORM:
                if self.context.email and not self.context.integration_form_sent:
                    self.send_integration_form(
                        self.context.email,
                        self.context.client_name or "there",
                        self.context.firm_name or "your firm"
                    )
        
        # Save conversation
        self.save_conversation()
        
        print("\n" + "="*70)
        print("✅ Conversation ended")
        print(f"Wanted human: {'Yes' if self.context.wants_human else 'No'}")
        print(f"Deal closed: {'Yes' if self.context.deal_closed else 'No'}")
        print(f"Total price: ${self.context.total_price:,.2f}")
        print("="*70)


if __name__ == "__main__":
    import sys
    
    # Create bot
    bot = VoiceSalesBot()
    
    # Run text conversation
    bot.run_text_conversation()