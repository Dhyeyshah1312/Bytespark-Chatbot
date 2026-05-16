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
            "meeting_time": None,
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
        # Do NOT seed purpose with generic service name anymore, so we force the 'What is it for?' question

    def update_state(self, user_input: str, extracted_name: str = None, extracted_email: str = None, mood="Neutral", engagement="Detailed"):
        self.turn_count += 1
        self.mood = mood
        self.engagement = engagement

        if extracted_name: self.lead["name"] = extracted_name
        if extracted_email: self.lead["email"] = extracted_email

        # Only advance stage when BOTH name and email are captured
        # Only advance stage when Name, Email, and Meeting Time are all captured
        if self.stage == "discovery" and self.lead["name"] and self.lead["email"] and self.lead["meeting_time"]:
            self.stage = "wrap_up"

    def get_directive(self) -> str:
        PROJECT_FIELDS = ["purpose", "audience", "platforms", "timeline", "budget"]
        CONTACT_FIELDS = ["name", "email"]

        if self.stage == "idle":
            return (
                "CONVERSATION STATUS: First interaction.\n"
                "GOAL: Greet the user as Spark from ByteSpark. Present our 7 core services as a clear, professional list or table:\n"
                "- 🌐 **Web Development** (Websites, Platforms)\n"
                "- 📱 **App Development** (iOS, Android)\n"
                "- ☁️ **Cloud Services** (Infrastructure, Hosting)\n"
                "- 🤖 **AI/ML Solutions** (Automation, Analytics)\n"
                "- 📈 **Digital Marketing** (Growth, Campaigns)\n"
                "- 🔍 **SEO Optimization** (Visibility)\n"
                "- 🎨 **UI/UX Design** (Prototyping, Interfaces)\n\n"
                "Ask which of these areas they are looking to explore for their project."
            )

        missing_project = [f for f in PROJECT_FIELDS if not self.lead.get(f)]
        missing_contact = [f for f in CONTACT_FIELDS if not self.lead.get(f)]
        synergies = self.SERVICE_SYNERGIES.get(self.service_context, ["SEO Optimization", "UI/UX Design"])

        # All 5 project fields are done — pivot to contact
        if not missing_project and missing_contact:
            needed = []
            if not self.lead.get("name"): needed.append("Name")
            if not self.lead.get("email"): needed.append("Email")
            
            return (
                f"### SALES DASHBOARD\n"
                f"- Project Status: Discovery Complete ✅\n"
                f"- Relevant Synergies: {synergies}\n"
                f"- Next Step: Capture {needed} and Strategic Cross-sell\n\n"
                f"**DIRECTIVE:**\n"
                f"1. Acknowledge their project fields.\n"
                f"2. **INTELLIGENT CROSS-SELL**: Based on their specific goals, suggest the MOST relevant service from {synergies} (e.g., 'Since you're focusing on fan engagement, we should also consider...').\n"
                f"3. Ask for their {needed} to prepare the proposal."
            )

        # Missing Meeting Time?
        if not missing_project and self.lead["name"] and self.lead["email"] and not self.lead["meeting_time"]:
            return (
                f"### SALES DASHBOARD\n"
                f"- Project Status: Lead Captured 📧\n"
                f"- Goal: Schedule Discovery Call\n\n"
                f"**DIRECTIVE:**\n"
                f"1. Acknowledge their contact info.\n"
                f"2. **BOOK THE MEETING**: Suggest a specific time tomorrow (e.g., 'Does 11 AM tomorrow work?'). If the user says 'yes' or 'anytime', lock in that specific time and move to wrap-up. DO NOT repeat the same time range."
            )

        # Everything collected — wrap up
        if not missing_project and self.lead["name"] and self.lead["email"] and self.lead["meeting_time"]:
            self.stage = "done"
            return (
                "### MISSION STATUS: COMPLETE ✅\n"
                "**DIRECTIVE: DO NOT ASK ANY MORE QUESTIONS.**\n"
                "1. Provide a final summary using this exact Markdown Table format:\n\n"
                "| Field | Detail |\n"
                "| :--- | :--- |\n"
                f"| **Name** | {self.lead['name']} |\n"
                f"| **Email** | {self.lead['email']} |\n"
                f"| **Purpose** | {self.lead['purpose']} |\n"
                f"| **Platforms** | {self.lead['platforms']} |\n"
                f"| **Timeline** | {self.lead['timeline']} |\n"
                f"| **Budget** | {self.lead['budget']} |\n"
                f"| **Meeting Schedule** | {self.lead['meeting_time']} |\n\n"
                "2. Confirm the proposal is being sent to their email.\n"
                "3. End the conversation warmly. Your job is done."
            )

        # Still gathering project fields
        gathered = {f: self.lead[f] for f in PROJECT_FIELDS if self.lead.get(f)}
        status = (
            f"### SALES DASHBOARD\n"
            f"- Project Focus: {self.service_context.upper()}\n"
            f"- Gathered so far: {gathered}\n"
            f"- Still needed (ask ONE at a time): {missing_project}\n"
            f"- User Mood: {self.mood} | Engagement: {self.engagement} | Turn: {self.turn_count}\n\n"
            f"**SALES GUIDANCE (Strategic):**\n"
            f"1. **VISION FIRST**: You are missing the project Purpose. You MUST ask about the user's specific vision or the problem they want to solve before asking for audience/platforms.\n"
            f"2. **STRICT DISCOVERY**: You are still missing {missing_project}. Ask about {missing_project[0]} next. DO NOT ask for name or email yet.\n"
            f"3. **Human Tone**: Keep it natural. Acknowledge and bridge.\n"
            f"4. **The Human Factor**: Only prioritize wrap-up if Turn Count is 12+ OR Mood is 'Frustrated'. Currently at Turn {self.turn_count}.\n"
        )
        return status

