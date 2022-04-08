from datetime import datetime

class Remind:
    def __init__(self, bot):
        self.bot = bot
        self.remind_next = []
        self.remind_next_cur = []
        self.movie_list = []
    
    async def send_in_channel(self):
        await self.bot.get_channel(self.bot.initial_channels[0]).send(msg)

    async def add_to_remind_next(self, name):
        # perma_pings = await self.get_perma_pings()
        # for perma_name in perma_pings:
        #     if name == perma_name[0]:
        #         return
        if not name in self.remind_next:
            self.remind_next.append(name)

    def add_to_remind_next_cur(self, hour, minute):
        self.remind_next_cur.append(
                self.bot.scheduler.add_job(
                    self.send_remind_next, 'cron', hour=hour, minute=minute
                    )
                )

    def clear_remind_next_cur(self):
        self.bot.logger.info(f"Clearing jobs and movie list")
        for x in self.remind_next_cur:
            x.remove()
        self.remind_next_cur = []

    async def get_perma_pings(self):
        return await self.bot.database.records(f"SELECT * FROM pinglist")

    async def add_perma_ping(self, name):
        await self.bot.database.execute(f"INSERT INTO pinglist(Username, Added) VALUES(\"{name}\", 1)")

    async def del_perma_ping(self, name):
        await self.bot.database.execute(f"DELETE FROM pinglist WHERE Username = \"{name}\"")

    async def check_perma_ping(self, name):
        record = await self.bot.database.record(f"SELECT * FROM pinglist WHERE Username = \"{name}\"")
        if record is None:
            return False
        return True

    async def send_remind_next(self):
        perma_pings = await self.get_perma_pings()
        for perma_name in perma_pings:
            # add perma pings to current remind
            self.remind_next.append(perma_name[0])
        cur_time = datetime.now().strftime("%H:%M")
        self.bot.logger.info(f"Movie list before ping: {self.movie_list}")
        if self.movie_list and self.movie_list[0][1] == cur_time:
            # add movie pings to current remind
            self.bot.logger.info(f"Pinging for movie {self.movie_list[0][0]}")
            cur_movie = self.movie_list[0]
            for username in cur_movie[2]:
                self.remind_next.append(username)
            base_msg = f"{cur_movie[0]} started DinkDonk"
            self.movie_list.pop(0)
        else:
            self.bot.logger.info(f"Found no movie, pinging generic")
            base_msg = "Next dlc started DinkDonk"
        self.remind_next = list(dict.fromkeys(self.remind_next)) # clear duplicate pings
        ping_msg = ""
        for ping in self.remind_next:
            if len(base_msg + ping_msg + ping) > 300:
                complete_msg = base_msg + ping_msg
                await self.bot.get_channel(self.bot.initial_channels[0]).send(complete_msg) 
                ping_msg = ""
                pass
            ping_msg += f" @{ping}"
        complete_msg = base_msg + ping_msg
        await self.bot.get_channel(self.bot.initial_channels[0]).send(complete_msg) 
        self.remind_next = []
