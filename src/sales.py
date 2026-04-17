class SalesAgent:

    def __init__(self):
        self.stage = "idle"
        self.lead = {}

    def start_flow(self, service=None):
        self.stage = "ask_name"
        return "Sure, let’s get that scheduled 👍\n\nMay I know your name?"

    def handle(self, user_input):

        if self.stage == "ask_name":
            self.lead["name"] = user_input
            self.stage = "ask_email"
            return "Thanks! What's the best email to reach you?"

        elif self.stage == "ask_email":
            self.lead["email"] = user_input
            self.stage = "schedule_meeting"
            return "Perfect. Let me set this up for you."

        return None