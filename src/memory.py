class ChatMemory:
    def __init__(self):
        self.history = []

    def add(self, user, bot):
        self.history.append({"user": user, "bot": bot})

    def get_context(self):
        context = ""
        for item in self.history[-3:]:
            context += f"User: {item['user']}\nBot: {item['bot']}\n"
        return context