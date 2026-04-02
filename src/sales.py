class SalesAgent:

    def __init__(self):
        self.stage = "idle"
        self.lead = {}

    def start_flow(self, service):
        self.stage = "ask_name"
        self.lead["service"] = service
        return f"Great choice! 🚀\n\nLet's get started.\n\nWhat's your name?"

    def handle(self, user_input):

        if self.stage == "ask_name":
            self.lead["name"] = user_input
            self.stage = "ask_email"
            return "Nice to meet you! What's your email?"

        elif self.stage == "ask_email":
            self.lead["email"] = user_input
            self.stage = "ask_project"
            return "Tell me about your project."

        elif self.stage == "ask_project":
            self.lead["project"] = user_input
            self.stage = "schedule_meeting"
            return "Perfect! Scheduling your meeting..."

        return None