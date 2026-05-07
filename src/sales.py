class SalesAgent:
    """
    State tracker for the sales conversation. 
    Does NOT generate responses; only tracks what information has been gathered.
    """

    def __init__(self):
        self.stage = "idle"
        self.lead = {
            "name": None,
            "email": None,
            "purpose": None,
            "audience": None,
            "platforms": None,
            "features": None,
            "timeline": None,
            "budget": None,
            "_lead_saved": False,
            "_meeting_saved": False
        }
        self.service_context = ""
        self.turn_count = 0

    def start_flow(self, service=None):
        self.stage = "discovery"
        self.service_context = service or "project"
        self.turn_count = 0
        return None  # Let the LLM handle the opening based on context

    def update_state(self, user_input: str, extracted_name: str = None, extracted_email: str = None):
        """Update the internal lead state based on LLM extractions or regex."""
        self.turn_count += 1
        
        if extracted_name:
            self.lead["name"] = extracted_name
        if extracted_email:
            self.lead["email"] = extracted_email

        # The stage transitions are now more fluid
        if self.stage == "discovery":
            if self.lead["name"] and self.lead["email"]:
                self.stage = "contact_info"
        
        if self.stage == "contact_info":
            if self.lead["name"] and self.lead["email"]:
                # If we have both, we can move to scheduling or wrapping up
                pass

    def get_directive(self) -> str:
        """Returns a hidden instruction for the LLM based on current state."""
        if self.stage == "idle":
            return ""

        # Define the full discovery path in order
        discovery_path = [
            ("purpose", "What is the core purpose or main goal of this project?"),
            ("audience", "Who is the target audience for this solution?"),
            ("platforms", "Which platforms should we target (iOS, Android, Web, etc.)?"),
            ("timeline", "Do you have a rough timeline or deadline in mind?"),
            ("budget", "Do you have a preliminary budget range for this project?"),
            ("name", "May I know your name?"),
            ("email", "What is your professional email address so our team can send a proposal?"),
        ]

        # Find the first missing item
        next_item = next((item for item in discovery_path if not self.lead.get(item[0])), None)

        if next_item:
            field_name, field_question = next_item
            
            # Transition stage if we've reached contact info
            if field_name in ["name", "email"]:
                self.stage = "contact_info"
            else:
                self.stage = "discovery"

            return (
                f"DIRECTIVE: We are in the {self.stage} phase for a {self.service_context}. "
                f"CRITICAL: You MUST ask ONLY ONE question at a time. "
                f"The next thing we need is the {field_name}. "
                f"Acknowledge the previous answer warmly, then ask: '{field_question}'"
            )
        else:
            # Everything gathered!
            self.stage = "wrap_up"
            return (
                "DIRECTIVE: We have everything we need (Project details, Timeline, Budget, and Contact Info)! "
                "DO NOT ask any more questions. Express great excitement, provide a brief summary table of the project, "
                "and propose a quick 15-minute discovery call. Provide ByteSpark's contact details clearly."
            )

    def handle(self, user_input):
        # We no longer use this for string generation
        return None
