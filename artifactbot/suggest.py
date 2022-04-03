class Suggest:
    def __init__(self, bot):
        self.bot = bot
    
    async def get_suggestions(self):
        return await self.bot.database.records(f"SELECT * FROM suggestions")

    async def add_suggestion(self, name, suggestion):
        await self.bot.database.execute(f"INSERT INTO suggestions(Username, Suggestion) VALUES(\"{name}\", \"{suggestion}\")")

    async def del_suggestion(self, name):
        await self.bot.database.execute(f"DELETE FROM suggestions WHERE Username = \"{name}\"")

    async def check_suggested(self, name):
        record = await self.bot.database.record(f"SELECT * FROM suggestions WHERE Username = \"{name}\"")
        if record is None:
            return False
        return True

    async def print_suggestions(self):
        suggestions = await self.get_suggestions()
        for suggestion in suggestions:
            print(suggestion)
            await self.del_suggestion(suggestion[0])
