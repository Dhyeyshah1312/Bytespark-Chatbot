class SalesAgent:

    def __init__(self):
        self.stage = "idle"
        self.lead = {}
        self.service_context = ""

    def start_flow(self, service=None):
        self.stage = "ask_timeline"
        self.service_context = service or "the project"
        return f"Great! To help me recommend the right approach for {self.service_context}, when are you hoping to launch? Do you have a target timeline in mind?"

    def handle(self, user_input):

        if self.stage == "ask_timeline":
            self.lead["timeline"] = user_input.strip()
            self.stage = "ask_budget"
            return "Thanks for sharing! What's your budget range for this project? This helps me recommend the best solution within your investment comfort zone."

        elif self.stage == "ask_budget":
            self.lead["budget"] = user_input.strip()
            self.stage = "ask_name"
            return "Perfect! Now I have a better understanding. May I know your name so we can discuss this further?"

        elif self.stage == "ask_name":
            self.lead["name"] = user_input.strip().title()
            self.stage = "ask_email"
            return f"Thanks {self.lead['name']}! What's the best email to reach you?"

        elif self.stage == "ask_email":
            self.lead["email"] = user_input.strip()
            self.stage = "schedule_meeting"
            return "Perfect! I have all your details. Our team will reach out to schedule a discovery call."

        return None
