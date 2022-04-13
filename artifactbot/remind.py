import datetime as dt
from apscheduler.jobstores.base import JobLookupError

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

    def next_datetime(self, current: dt.datetime, hour, minute) -> dt.datetime:
        repl = current.replace(hour=hour, minute=minute)
        while repl <= current:
            repl = repl + dt.timedelta(days=1)
        return repl

    def add_to_remind_next_cur(self, hour, minute):
        now = dt.datetime.now()
        time_to_run = self.next_datetime(current=now, hour=hour, minute=minute)
        self.remind_next_cur.append(
                self.bot.scheduler.add_job(
                    self.send_remind_next, 'date', run_date=time_to_run
                    )
                )
        self.bot.logger.info(f"job scheduled to run at {time_to_run}")

    def clear_remind_next_cur(self):
        self.bot.logger.info(f"Clearing jobs and movie list")
        self.bot.logger.info(self.remind_next_cur)
        for x in self.remind_next_cur:
            try:
                x.remove()
            except JobLookupError:
                pass
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
        current = dt.datetime.now().strftime("%H:%M")
        cur_time = [current, current[1:]] if current.startswith('0') else [current]
        self.bot.logger.info(f"Movie list before ping: {self.movie_list}")
        if self.movie_list:
            if self.movie_list[0][1] in cur_time:
                # add movie pings to current remind
                self.bot.logger.info(f"Pinging for movie {self.movie_list[0][0]}")
                cur_movie = self.movie_list[0]
                for username in cur_movie[2]:
                    self.remind_next.append(username)
                base_msg = f"{cur_movie[0]} starting DinkDonk"
                self.movie_list.pop(0)
            else:
                self.bot.logger.info("Pinging generic")
                self.bot.logger.info(f"Current time: {cur_time}, Movie list: {self.movie_list}")
                base_msg = "Next dlc starting DinkDonk"
        else:
            self.bot.logger.info("Found no movie list, pinging generic")
            base_msg = "Next dlc starting DinkDonk"
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
