class SalesAgent:
    """
    Fluid Strategic Consultant State Tracker.
    Now uses a "Status Dashboard" approach instead of rigid commands.
    """
    
    SERVICE_SYNERGIES = {
        "web development": ["SEO Optimization", "UI/UX Design"],
        "app development": ["Cloud Services", "Digital Marketing"],
        "cloud services": ["AI/ML Solutions", "SEO Optimization"],
        "ai/ml solutions": ["Cloud Services", "UI/UX Design"],
        "digital marketing": ["SEO Optimization", "Web Development"],
        "seo optimization": ["Digital Marketing", "Web Development"],
        "ui/ux design": ["Web Development", "App Development"],
        "general inquiry": ["Web Development", "AI/ML Solutions"]
    }

    def __init__(self):
        self.stage = "idle"
        self.lead = {
            "name": None,
            "email": None,
            "purpose": None,
            "audience": None,
            "platforms": None,
            "timeline": None,
            "budget": None,
            "_lead_saved": False,
        }
        self.service_context = "general inquiry"
        self.turn_count = 0
        self.mood = "Neutral"
        self.engagement = "Detailed"

    def start_flow(self, service=None):
        self.stage = "discovery"
        self.service_context = (service or "general inquiry").lower()
        self.turn_count = 0

    def update_state(self, user_input: str, extracted_name: str = None, extracted_email: str = None, mood="Neutral", engagement="Detailed"):
        self.turn_count += 1
        self.mood = mood
        self.engagement = engagement
        
        if extracted_name: self.lead["name"] = extracted_name
        if extracted_email: self.lead["email"] = extracted_email

        if self.stage == "discovery" and self.lead["name"] and self.lead["email"]:
            self.stage = "contact_info"

    def get_directive(self) -> str:
        if self.stage == "idle":
            return (
                "CONVERSATION STATUS: Starting chat.\n"
                "GOAL: Introduce yourself as Spark from ByteSpark. Share our FULL catalog of 7 services: "
                "Web Development, App Development, Cloud Services, AI/ML Solutions, Digital Marketing, SEO Optimization, and UI/UX Design. "
                "Ask how you can help bring their technology vision to life today."
            )

        """Generates a strategic dashboard for the LLM based on current status."""
        missing = [k for k, v in self.lead.items() if v is None and not k.startswith("_")]
        synergies = self.SERVICE_SYNERGIES.get(self.service_context, ["SEO Optimization", "UI/UX Design"])

        status = f"""
### 📊 STRATEGIC SALES DASHBOARD
- Project Focus: {self.service_context.upper()}
- Information Gathered: {len(self.lead) - len(missing)}/{len(self.lead)} fields known
- Missing Details: {missing}
- User Dynamics: {self.mood} / {self.engagement}
- Conversation Depth: Turn {self.turn_count}

**SALES GUIDANCE (Strategic):**
1. **The Lead Mission**: Your goal is to gather these 5 specific fields: **Purpose, Audience, Platforms, Timeline, Budget**. 
2. **NO AUDITING**: Never ask about their current manual business operations (e.g., 'How do you take orders?', 'How many staff?'). Focus entirely on the future digital project.
3. **Bridge & Pivot**: Once you have the 5 fields, pivot to getting their **Email** to 'send a formal proposal' and book a discovery call.
4. **Natural Flow**: Don't force all questions at once. Ask one logical question from the 'Missing Details' list at a time.
5. **Natural Pivot**: If the user says 'no idea', 'you do it', or 'nope', accept that as a final answer for that field and move on.
6. **Synergy Suggestion**: Consider how {synergies[0]} or {synergies[1]} would benefit this specific project.
7. **Consultative upsell**: Suggest other relevant services to the user seems genuinely interested and has provided complete details. 
8. **Polite Persistence**: If the user is dodging questions or giving vague answers, be gently persistent. 
9. **The Human Factor**: If Turn Count is 5+ or the Mood is 'Frustrated', prioritize a professional wrap-up over more data collection.
"""
        if not missing and self.lead.get("email"):
            self.stage = "done"
            return "CONVERSATION COMPLETE. Thank them professionally and end the chat."
            
        return status
