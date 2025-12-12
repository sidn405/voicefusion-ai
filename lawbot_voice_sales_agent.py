"""
LawBot 360 Voice Sales Agent - OpenAI Version
Handles complete sales flow from cold call to payment and onboarding
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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
            "integration_form_sent": self.integration_form_sent
        }


class VoiceSalesBot:
    """Main voice sales bot with AI conversation and voice capabilities"""
    
    def __init__(self):
        # Initialize OpenAI
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4-turbo-preview"  # or "gpt-4o" or "gpt-3.5-turbo"
        
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
                    "price": 2000,
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
You are a confident, direct sales representative for 4D Gaming, making a cold call to sell LawBot 360.

GOAL: Get their name and permission to continue (30 seconds max)

SCRIPT:
"Hi! This is [name] from 4D Gaming. I'm calling law firms that are losing leads outside business hours. Is this something that affects you?"

- Get their name quickly
- Identify if decision-maker (don't waste time on gatekeepers)
- Get permission to continue: "Do you have 5 minutes? I can show you how to capture those missed leads today."

DO NOT:
- Offer to schedule a call later
- Ask for "best time to talk"
- Be overly polite and waste time

REMEMBER: You're here to SELL TODAY, not book meetings.
""",
            
            ConversationStage.DISCOVERY: """
GOAL: Quickly identify 1-2 pain points (2 minutes max)

ASK ONLY THESE:
1. "How do you handle leads that come in after 5pm or on weekends?"
2. "What happens when your receptionist is out sick or on vacation?"

LISTEN FOR:
- "We miss them" = PAIN POINT
- "They wait until next day" = PAIN POINT  
- "Partner answers phone" = PAIN POINT

AS SOON AS you hear a pain point, IMMEDIATELY transition to solution:
"That's exactly what I'm calling about. Let me show you how LawBot 360 solves that..."

DO NOT:
- Ask 10 discovery questions
- Do deep needs analysis
- Schedule follow-up discovery call

You're here to SELL, not consult. Get 1 pain point and PITCH.
""",
            
            ConversationStage.SOLUTION_PRESENTATION: """
GOAL: Quick pitch (1 minute) then GO TO PRICING

PITCH:
"LawBot 360 is your complete AI intake system. Works 24/7 across all your practice areas - 
Personal Injury, Family Law, Criminal, Immigration, Estate - with custom scripts for each.
Uploads documents, schedules consults, integrates with Clio/Salesforce, sends follow-ups.

Most firms sign up 5-10 new clients per month just from after-hours leads they were missing.
That's $500k to $1M per year in captured revenue."

THEN IMMEDIATELY:
"The investment is $25,000 one-time for the complete system. Most firms see full ROI 
in 30-60 days from just 2-3 extra cases. We can get you live in 6 weeks. Sound good?"

DO NOT:
- Give long feature presentations
- Offer to send information
- Schedule demo calls
- Say "let me tell you more"

CLOSE NOW. At $25k, every minute counts.
""",
            
            ConversationStage.PRICING_DISCUSSION: """
GOAL: State price confidently and CLOSE

PRICE STATEMENT:
"$25,000 one-time for the complete system. That includes everything - custom scripts for all 
your practice areas, integrations, training, the works. No monthly fees unless you want ongoing support.

You pay 30% now to start, 50% when we're building it, 20% when we launch.
So $7,500 to get started today."

THEN TRIAL CLOSE:
"Does that work for you?"

IF THEY HESITATE:
"Think about it - you're missing 5-10 qualified leads every month. At your case values, that's 
easily $500k to $1M in lost revenue per year. $25,000 is 2-3 cases worth of fees. 
You'll make this back in 30-60 days. This is basically insurance against lost revenue."

IF PRICE OBJECTION:
"I get it, $25,000 is a real investment. But what's the cost of NOT having this? 
How much is a good Personal Injury case worth? $50k? $100k? $500k?

You're losing cases EVERY MONTH to competitors who respond faster. If LawBot captures just 
2-3 of those cases, you're already at $100k-500k in fees. The math is simple."

THEN CLOSE:
"Let's get you set up. I'll walk you through payment right now - takes 2 minutes. Ready?"

DO NOT:
- Offer payment plans beyond the milestones
- Offer discounts (you'll train them to negotiate)
- Say "I'll send a proposal"
- Schedule a follow-up call

This is a premium product at a premium price. CLOSE. NOW.
""",
            
            ConversationStage.ADDONS_PRESENTATION: """
GOAL: Quick upsell (30 seconds max), then move to close

ONLY IF they seem very interested and have budget:
"Quick question - do you also need native mobile apps? iOS and Android. 
Adds $5,000 but gives you App Store presence. Want it?"

OR if multi-location:
"By the way - do you have multiple office locations? We can set up multi-location support 
for $3,000. Keeps everything connected. Need that?"

IF YES: Add to price, then CLOSE
IF NO: "No problem. Base system it is. Let's get you started..."

AVAILABLE ADD-ONS (only mention if relevant):
- Native iOS & Android apps: $5,000
- Multi-language support: $1,500  
- Advanced Analytics dashboard: $2,000
- SMS/WhatsApp integration: $1,000
- Multi-location support: $3,000

DO NOT:
- Present all add-ons
- Explain features in detail
- Delay the close

The goal is base sale ($25,000). Add-ons are OPTIONAL quick upsells only.
""",
            
            ConversationStage.MAINTENANCE_PLANS: """
GOAL: Mention it exists, move on (15 seconds)

"One more thing - ongoing maintenance is optional. Most firms choose Basic at $497/month 
for server hosting, updates, and support. Or you can self-manage at no cost - though 
that's not recommended.

Want Basic maintenance included?"

IF YES: Note it, then CLOSE
IF NO: "No problem - you can add it later. Let's get you set up..."

AVAILABLE PLANS (only if they ask):
- Basic: $497/mo (hosting, updates, email support)
- Professional: $997/mo (priority support, optimization calls)
- Enterprise: $1,997/mo (dedicated manager, 24/7 support)
- None: Self-managed (not recommended)

DO NOT:
- Explain all 4 plans
- Try hard to upsell maintenance
- Make it seem required

Mention Basic exists ($497/mo) and MOVE TO CLOSE immediately.
""",
            
            ConversationStage.CLOSING: """
GOAL: Close the sale RIGHT NOW

ASSUMPTIVE CLOSE:
"Alright [Name], let's get you set up. I'm pulling up your account now.
I'll need your email to send the portal link and your card info to process the first milestone - $7,500.
What's your email address?"

IF THEY HESITATE:
"Look, I've closed hundreds of these deals. The firms that move fast see results fast.
The ones that 'think about it' call me back in 6 months after they've lost another 
$500k in cases to faster competitors.

At $25,000, this is 2-3 good cases worth of fees. You're losing more than that 
EVERY MONTH right now. Which firm do you want to be?"

SILENCE CLOSE:
Ask for the sale, then SHUT UP. First person to speak loses.
"So should we get started today?"
[SILENCE - count to 10]

ALTERNATIVE OF CHOICE:
"Would you like to start with the base system at $25,000, or add mobile apps for $30,000 total?"
(Makes them choose between options, not yes/no)

VALUE REFRAME:
"$25,000 sounds like a lot until you realize you're losing 10x that in revenue every month.
This isn't a cost - it's a profit center that pays for itself in 30-60 days."

DO NOT:
- Say "would you like to think about it?"
- Offer to email information
- Schedule a follow-up call
- Give them an out

You've made the pitch. You've handled objections. NOW CLOSE.

If they say YES: "Perfect! Let me get your email..."
If they say NO: "What's holding you back?" [Handle objection, close again]
""",
            
            ConversationStage.PORTAL_SIGNUP: """
GOAL: Get them into portal RIGHT NOW

"Perfect! I'm sending you the portal link to {email} right now. Check your email - it should hit your inbox in 30 seconds.

While you're pulling that up, here's what to do:
1. Click the link
2. Create password
3. You'll see the payment page for Milestone 1 ($7,500)

Got the email yet? Click that link and let me know when you see the payment page."

STAY ON THE PHONE: Don't let them go "look at it later". Walk them through NOW.

IF THEY HESITATE:
"I'll stay on the line while you do this. Takes 2 minutes and then you're all set. 
$7,500 to get started and you're live in 2 weeks capturing those lost leads. 
Pull up your email - checking now?"
""",
            
            ConversationStage.PAYMENT_SETUP: """
GOAL: Get payment processed RIGHT NOW

"Alright, you should see the payment page. It's asking for $7,500 - that's your 30% to kick things off.

Just enter your card info and hit submit. I'll wait - go ahead."

IF THEY ASK ABOUT MILESTONES:
"Quick rundown: $7,500 now to start. $12,500 when we're halfway done and you approve everything. 
$5,000 when we launch. Total $25,000. Make sense? Cool, go ahead and enter that card."

STAY ON THE PHONE: Don't let them "do it later". Process payment NOW.

WHEN PAYMENT GOES THROUGH:
"Perfect! Payment processed. You're officially starting within 48 hours. 
Your project is funded and we're moving forward. Confirmation email hitting your inbox now 
with your kickoff call details."

Then move immediately to integration form stage.
""",
            
            ConversationStage.INTEGRATION_FORM: """
GOAL: Send integration form to collect technical details

EXPLAIN:
"Perfect! Your first milestone is funded. Here's what happens next:

1. You'll receive an email with our System Integration Form
2. This collects technical details about your website, current systems, and requirements
3. Fill it out at your convenience (takes about 10 minutes)
4. Our team reviews it and schedules your kickoff call within 48 hours

SEND FORM: "I'm sending that integration form to {email} right now..."

CHECK: "Do you have any questions about the form or next steps?"
""",
            
            ConversationStage.NEXT_STEPS: """
GOAL: Set clear expectations for what happens next

TIMELINE:
"Here's your project timeline:

This Week:
- Complete the integration form
- We'll reach out to schedule your kickoff call

Days 1-3:
- Kickoff call to review requirements
- Design mockups and bot personality development
- You review and provide feedback

Days 6-8:
- Development begins after your approval
- Milestone 2 payment due when we start development

Days 3:
- Testing and development
- Your team training
- Final Milestone 3 payment
- Go live!

SUPPORT: Throughout the project, you can reach us through the portal, email, or phone.

Any questions about the process?"
""",
            
            ConversationStage.COMPLETED: """
GOAL: Warm close and build relationship

CLOSING:
"[Client Name], thank you for choosing 4D Gaming and LawBot 360! We're excited to work with [Firm Name].

NEXT STEPS RECAP:
1. Check your email for the integration form
2. Complete it at your convenience
3. We'll reach out within 48 hours to schedule kickoff

SUPPORT:
- Questions? Email us or message through the portal
- Track progress anytime at [portal URL]

We look forward to helping you capture more leads and grow your practice!

Any final questions before we wrap up?"
"""
        }
        
        return stage_scripts.get(self.context.current_stage, "Continue the conversation professionally.")
    
    def create_system_prompt(self) -> str:
        """Create comprehensive system prompt for OpenAI"""
        
        milestone_1 = self.context.total_price * 0.30
        milestone_2 = self.context.total_price * 0.50
        milestone_3 = self.context.total_price * 0.20
        
        return f"""You are a CLOSER - an expert cold caller selling LawBot 360 for 4D Gaming.

CRITICAL: Your job is to CLOSE THE SALE on THIS call. NOT to schedule demos, consultations, or follow-ups.

CURRENT CONVERSATION STAGE: {self.context.current_stage.value}

CLIENT CONTEXT:
- Name: {self.context.client_name or "Not captured yet - GET THIS FIRST"}
- Firm: {self.context.firm_name or "Not captured"}
- Email: {self.context.email or "NEED THIS TO CLOSE"}
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

Quick pitch: "Complete AI intake system for all practice areas. Custom scripts, integrations, 
document handling. $25,000 one-time. Most firms capture $500k-$1M in lost revenue first year."

SALES RULES - FOLLOW THESE RELIGIOUSLY:

1. MOVE FAST: Get name → Find pain → Pitch → Quote price → Close. Under 10 minutes total.

2. NO DEMOS/CONSULTATIONS: Never say:
   - "Let me schedule a demo"
   - "When's a good time to talk?"
   - "I'll send you information"
   - "Think about it and get back to me"
   You close TODAY or you lose the deal.

3. ASSUMPTIVE CLOSE: Act like they've already bought:
   - "Let me get your email to send the portal link..."
   - "I'm pulling up your account now..."
   - "What card should I charge the $1,498 to?"

4. HANDLE OBJECTIONS IMMEDIATELY:
   - "Too expensive" → "What's a new client worth to you? $10k? $50k? This pays for itself with ONE case."
   - "Need to think" → "What specifically? If it's money, we do payment plans. If it's timing, we launch in 6 weeks."
   - "Talk to partner" → "Of course. Let's get them on the line right now. I'll wait."
   
5. USE SILENCE: After asking for the sale, SHUT UP. Let them speak first.

6. ALTERNATIVE CLOSE: Don't ask yes/no. Ask: "Should we start with base or add document automation?"

7. PAIN → SOLUTION → PRICE → CLOSE: That's it. No fluff.

8. OFF-TOPIC = REDIRECT: "That's interesting! But back to capturing those lost leads..."

9. BE CONFIDENT: You KNOW this solves their problem. Act like it.

10. CLOSE MULTIPLE TIMES: If they say no, find out why, handle it, close again. Minimum 3 closes per call.

OUTPUT FORMAT:
- Keep responses SHORT (1-2 sentences max)
- Sound human, not scripted
- Always be moving toward the close
- If they agree to anything, immediately ask for email/payment

REMEMBER: You're a CLOSER, not a consultant. Your metric is SALES TODAY, not meetings scheduled.

Every response should either:
A) Move closer to the close, OR
B) Handle an objection to enable the close

If you're not closing, you're losing."""
    
    def chat_with_gpt(self, user_message: str) -> str:
        """Get AI response from OpenAI"""
        
        # Add user message to history
        self.context.add_message("user", user_message)
        
        # Build messages for OpenAI
        messages = [
            {"role": "system", "content": self.create_system_prompt()}
        ]
        
        # Add conversation history (last 10 messages for context)
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
            assistant_message = "I apologize, I'm having a technical issue. Could you repeat that?"
        
        # Add assistant response to history
        self.context.add_message("assistant", assistant_message)
        
        # Extract information from conversation
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
        
        # Extract pain points
        pain_indicators = ["frustrated", "problem", "issue", "difficult", "challenge", "struggle"]
        if any(indicator in user_lower for indicator in pain_indicators):
            self.context.pain_points.append(user_message)
    
    def maybe_advance_stage(self, assistant_message: str):
        """Determine if conversation should advance to next stage"""
        
        message_lower = assistant_message.lower()
        
        # Stage advancement logic
        stage_transitions = {
            ConversationStage.GREETING: {
                "next": ConversationStage.DISCOVERY,
                "triggers": ["tell me about", "how do you", "what's your"]
            },
            ConversationStage.DISCOVERY: {
                "next": ConversationStage.SOLUTION_PRESENTATION,
                "triggers": ["sounds like", "lawbot can help", "exactly what we need"]
            },
            ConversationStage.SOLUTION_PRESENTATION: {
                "next": ConversationStage.PRICING_DISCUSSION,
                "triggers": ["how much", "what's the cost", "investment", "price"]
            },
            ConversationStage.PRICING_DISCUSSION: {
                "next": ConversationStage.ADDONS_PRESENTATION,
                "triggers": ["what else", "add-ons", "additional features"]
            },
            ConversationStage.ADDONS_PRESENTATION: {
                "next": ConversationStage.MAINTENANCE_PLANS,
                "triggers": ["maintenance", "ongoing", "support"]
            },
            ConversationStage.MAINTENANCE_PLANS: {
                "next": ConversationStage.CLOSING,
                "triggers": ["let's do it", "sounds good", "move forward"]
            },
            ConversationStage.CLOSING: {
                "next": ConversationStage.PORTAL_SIGNUP,
                "triggers": ["yes", "ready", "let's get started"]
            }
        }
        
        current_transition = stage_transitions.get(self.context.current_stage)
        if current_transition:
            triggers = current_transition["triggers"]
            if any(trigger in message_lower for trigger in triggers):
                self.context.current_stage = current_transition["next"]
                print(f"\n[STAGE ADVANCED: {self.context.current_stage.value}]\n")
    
    def speak(self, text: str, output_file: str = "bot_response.wav"):
        """Convert text to speech with cloned voice"""
        
        print(f"🗣️  Bot: {text}")
        
        try:
            self.tts.tts_to_file(
                text=text,
                file_path=output_file,
                speaker_wav=self.reference_voice,
                language="en",
                split_sentences=True
            )
            
            # Play audio (platform-specific)
            self.play_audio(output_file)
            
        except Exception as e:
            print(f"Voice generation error: {e}")
    
    def play_audio(self, audio_file: str):
        """Play audio file"""
        import platform
        import subprocess
        
        system = platform.system()
        
        try:
            if system == "Windows":
                import winsound
                winsound.PlaySound(audio_file, winsound.SND_FILENAME)
            elif system == "Darwin":  # macOS
                subprocess.call(["afplay", audio_file])
            else:  # Linux
                subprocess.call(["aplay", audio_file])
        except Exception as e:
            print(f"Audio playback error: {e}")
    
    def listen(self, timeout: int = 5) -> Optional[str]:
        """Listen for user speech and convert to text"""
        
        print("🎤 Listening...")
        
        with self.microphone as source:
            # Adjust for ambient noise
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            try:
                audio = self.recognizer.listen(source, timeout=timeout)
                text = self.recognizer.recognize_google(audio)
                print(f"👤 User: {text}")
                return text
            
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                print("Could not understand audio")
                return None
            except sr.RequestError as e:
                print(f"Speech recognition error: {e}")
                return None
    
    def send_integration_form(self, email: str, client_name: str, firm_name: str):
        """Send integration form to client"""
        
        # Email configuration
        sender_email = os.getenv("RESEND_EMAIL")
        sender_password = os.getenv("RESEND_PASSWORD")
        
        # Create email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"LawBot 360 System Integration Form - {firm_name}"
        msg["From"] = sender_email
        msg["To"] = email
        
        # Email body with link
        integration_form_url = os.getenv("INTEGRATION_FORM_URL", "https://4dgaming.games/client-integration.html")
        
        html_body = f"""
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
                
                <p>Questions? Reply to this email or call us at (555) 123-4567</p>
                
                <p>Track your project progress anytime at: <a href="https://4dgaming.games">https://4dgaming.games</a></p>
                
                <p>Best regards,<br/>
                The 4D Gaming Team</p>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, "html"))
        
        # Send email
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            print(f"✅ Integration form sent to {email}")
            self.context.integration_form_sent = True
            
        except Exception as e:
            print(f"❌ Email send error: {e}")
    
    def save_conversation(self):
        """Save conversation to file"""
        
        filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.context.to_dict(), f, indent=2)
        
        print(f"💾 Conversation saved: {filename}")
    
    def run_voice_conversation(self):
        """Main conversation loop with voice"""
        
        print("\n" + "="*70)
        print("🤖 LawBot 360 Voice Sales Agent (OpenAI)")
        print("="*70)
        print("\nStarting conversation...\n")
        
        # Opening message
        opening = "Hi! This is calling from 4D Gaming. Quick question - are you losing leads outside business hours, nights and weekends? We fix that. Got 5 minutes?"
        
        self.speak(opening)
        
        # Conversation loop
        while self.context.current_stage != ConversationStage.COMPLETED:
            # Listen for user response
            user_input = self.listen(timeout=10)
            
            if not user_input:
                # No response - prompt again
                prompt = "Are you still there?"
                self.speak(prompt)
                continue
            
            # Get AI response
            bot_response = self.chat_with_gpt(user_input)
            
            # Speak response
            self.speak(bot_response)
            
            # Check if deal closed and need to handle portal/payment
            if self.context.current_stage == ConversationStage.PORTAL_SIGNUP:
                # Send portal link
                if self.context.email:
                    portal_message = f"I've just sent a link to {self.context.email} to access our client portal. Check your email and I'll walk you through the signup."
                    self.speak(portal_message)
            
            elif self.context.current_stage == ConversationStage.INTEGRATION_FORM:
                # Send integration form
                if self.context.email and not self.context.integration_form_sent:
                    self.send_integration_form(
                        self.context.email,
                        self.context.client_name or "there",
                        self.context.firm_name or "your firm"
                    )
                    
                    confirmation = f"Perfect! I've sent the integration form to {self.context.email}. You should receive it within the next few minutes. Check your spam folder if you don't see it. Take your time completing it, and we'll reach out within 48 hours to schedule your kickoff call."
                    self.speak(confirmation)
            
            # Auto-save conversation every 5 messages
            if len(self.context.conversation_history) % 5 == 0:
                self.save_conversation()
        
        # Closing
        closing_message = "Thanks so much for your time today! We're excited to work with you. Have a great day!"
        self.speak(closing_message)
        
        # Final save
        self.save_conversation()
        
        print("\n" + "="*70)
        print("✅ Conversation completed!")
        print(f"Deal closed: {'Yes' if self.context.deal_closed else 'No'}")
        print(f"Total price: ${self.context.total_price}")
        print(f"Integration form sent: {'Yes' if self.context.integration_form_sent else 'No'}")
        print("="*70)
    
    def run_text_conversation(self):
        """Run conversation in text mode (no voice)"""
        
        print("\n" + "="*70)
        print("🤖 LawBot 360 Sales Agent (OpenAI - Text Mode)")
        print("="*70)
        print("Type your responses. Type 'quit' to exit.\n")
        
        # Opening message
        opening = "Hi! This is calling from 4D Gaming. Quick question - are you losing leads outside business hours, nights and weekends? We fix that. Got 5 minutes?"
        
        print(f"🤖 Bot: {opening}\n")
        
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
            
            print(f"\n🤖 Bot: {bot_response}\n")
            
            # Handle stage-specific actions
            if self.context.current_stage == ConversationStage.PORTAL_SIGNUP:
                if self.context.email:
                    print(f"\n[System: Portal link would be sent to {self.context.email}]")
            
            elif self.context.current_stage == ConversationStage.INTEGRATION_FORM:
                if self.context.email and not self.context.integration_form_sent:
                    print(f"\n[System: Integration form would be sent to {self.context.email}]")
                    self.context.integration_form_sent = True
        
        # Save conversation
        self.save_conversation()
        
        print("\n" + "="*70)
        print("✅ Conversation ended")
        print(f"Deal closed: {'Yes' if self.context.deal_closed else 'No'}")
        print(f"Total price: ${self.context.total_price}")
        print("="*70)


if __name__ == "__main__":
    import sys
    
    # Check mode
    mode = sys.argv[1] if len(sys.argv) > 1 else "text"
    
    # Create bot
    bot = VoiceSalesBot()
    
    if mode == "voice":
        bot.run_voice_conversation()
    else:
        bot.run_text_conversation()