class Memory:
    def __init__(self):
        self.history = []

    def add(self, user, bot):
        self.history.append((user, bot))

    def get_context(self):
        context = ""
        for u, b in self.history[-5:]:
            context += f"User: {u}\nAssistant: {b}\n"
        return context