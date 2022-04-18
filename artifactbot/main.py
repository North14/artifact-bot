from twitchio.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import os
import time
import logging
import re
import sys

from remind import Remind
from db import Database
from suggest import Suggest

def parse_movie_list(movie_list):
    movie_list = re.sub("^.* UTC\+2] ", '', str(movie_list))
    movie_list = re.split(" ⏩ ", str(movie_list))
    list1 = []
    for x in movie_list:
        time = re.search(r"([01]?[0-9]|2[0-3]):[0-5][0-9]", x).group()
        movie = re.sub(r" \(([01]?[0-9]|2[0-3]):[0-5][0-9]\)", '', x)
        list1.append([movie, time])
    return list1

def get_logger(log_file=""):
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    log = logging.getLogger()
    log.setLevel(level=logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setLevel(level=logging.INFO)
    sh.setFormatter(formatter)
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setLevel(level=logging.DEBUG)
        fh.setFormatter(formatter)
        log.addHandler(fh)
    log.addHandler(sh)
    return log

class Bot(commands.Bot):

    def __init__(self):
        self.token = os.getenv('twitch_oauth')
        self.prefix = os.getenv('bot_prefix', '+')
        self.initial_channels = os.getenv('bot_initial_channels').split(' ')
        self.owners = os.getenv('bot_owners').split(' ')

        self.scheduler = AsyncIOScheduler()
        self.scheduler.configure(timezone='cet')
        self.logger = get_logger(log_file="artifact.log")

        self.remind = Remind(self)
        self.database = Database(self)
        self.suggest = Suggest(self)
        super().__init__(token=self.token, prefix=self.prefix, initial_channels=self.initial_channels)

    async def event_ready(self):
        # TODO import variables from disk
        self.logger.info(f'Logged in as | {self.nick}')
        await self.database.connect()
        self.logger.info("Database connected")
        self.scheduler.start()
        self.logger.info("Scheduler started")
        self.scheduler.add_job(self.database.commit, 'cron', second=0)
        self.logger.info("Database commit schedule started")
        self.channel: twitchio.Channel = self.get_channel(
                next(iter(self.initial_channels))
        )
        await self.channel.send("Bot is now online!")

    async def event_message(self, message):
        if message.echo: return
        edit_msgs = [
                "!cmd edit !time",
                "!cmd edit time",
                "!command edit !time",
                "!command edit time"
                ]
        if message.content.lower().startswith(tuple(edit_msgs)):
            await self.parse_list(message.content)
            return
        await self.handle_commands(message)

    @commands.command()
    async def clear(self, ctx: commands.Context):
        if not ctx.author.name in self.owners: return
        self.remind.clear_remind_next_cur()
        self.remind.movie_list = []
        await ctx.send("List cleared")

    @commands.command()
    async def jobs(self, ctx: commands.Context):
        if not ctx.author.name in self.owners: return
        await ctx.send(f"{len(self.remind.remind_next_cur)} jobs loaded")
        # await ctx.send(f"There are ({len(self.scheduler.get_jobs()):,} jobs in queue")

    @commands.command(name="shutdown", aliases=["reboot", "restart", "update"])
    async def shutdown_command(self, ctx: commands.Context):
        # TODO write variables to disk
        if not ctx.author.name in self.owners: return
        await ctx.send(f"Shutting down")
        self.logger.info("Shutting down from shutdown command")
        self.scheduler.shutdown()
        await self.database.disconnect()
        sys.exit(0)

    @commands.command(name="ping", aliases=["info"])
    async def ping_command(self, ctx: commands.Context):
        cur_time = datetime.now().strftime("%H:%M")
        uptime = time.time() - start_time
        mm, ss = divmod(uptime, 60)
        uptime_string = f"{int(mm)}m {int(ss)}s"
        if mm >= 60:
            hh, mm = divmod(mm, 60)
            uptime_string = f"{int(hh)}h {int(mm)}m"
            if hh >= 24:
                dd, hh = divmod(hh, 24)
                uptime_string = f"{int(dd)}d {int(hh)}h"
        await ctx.send(f"Current time: {cur_time} | Uptime: {uptime_string}")

    @commands.command()
    async def trigger(self, ctx: commands.Context):
        if not ctx.author.name in self.owners: return
        await self.remind.send_remind_next()

    @commands.command(name="say", aliases=["echo"])
    async def echo_command(self, ctx: commands.Context):
        if not ctx.author.name in self.owners: return
        await ctx.send(" ".join(ctx.message.content.split(" ")[1:]))

    @commands.command(name="time", aliases=["list"])
    async def update_movie_list(self, ctx: commands.Context):
        # TODO: parse list when adding to streamelements too
        if not ctx.author.name in self.owners: return
        await self.parse_list(ctx.message.content)

    async def parse_list(self, movie_list):
        movies = parse_movie_list(movie_list)
        #  [["movie1", "12:34"], ["movie2", "23:12"]]
        
        cur_movie_list = self.remind.movie_list
        self.remind.movie_list = []
        self.remind.clear_remind_next_cur()
        cur_time = datetime.now().strftime("%H:%M")
        temp_thingy = False
        for movie in movies:
            movie.append([])
            self.logger.info(movie)
            if not temp_thingy:
                if datetime.strptime(cur_time, "%H:%M") < datetime.strptime(movie[1], "%H:%M"):
                    temp_thingy = True
                else:
                    self.logger.info(f"{movie[0]} already played")
            if temp_thingy:
                if cur_movie_list:
                    for cur_movie in cur_movie_list:
                        if cur_movie[0].lower() == movie[0].lower():
                            self.logger.info(f"Loading pings from {cur_movie}")
                            movie[2] = cur_movie[2]
                self.logger.info(f"Adding job: {movie}")
                self.remind.movie_list.append(movie)
                # TODO
                hour, minute = list(map(int, movie[1].split(':')))
                self.remind.add_to_remind_next_cur(hour, minute)
        self.logger.info(self.remind.movie_list)
        await self.channel.send(f"{len(self.remind.remind_next_cur)} jobs loaded")
        # await self.channel.send(f"{len(self.scheduler.get_jobs()):,} jobs loaded")

    @commands.command(name="suggest")
    async def add_suggest(self, ctx: commands.Context):
        msgs = ctx.message.content.split(" ")
        username = ctx.author.name
        try:
            msgs[1]
        except:
            await ctx.send(f"@{username} Usage: +suggest <suggestion here>")
            return
        msgs = " ".join(msgs[1:])
        if await self.suggest.check_suggested(username):
            await ctx.send(f"You already have an active suggestion ")
            return
        await self.suggest.add_suggestion(username, msgs)
        await ctx.send(f"@{username} suggestion added")

    @commands.command()
    async def suggestions(self, ctx: commands.Context):
        if not ctx.author.name in self.owners: return
        await self.suggest.print_suggestions()

    @commands.command(name="remind", aliases=["remindme", "pingme"])
    async def reminder(self, ctx: commands.Context):
        msgs = ctx.message.content.split(" ")
        self.logger.debug(msgs)
        try:
            if msgs[1] == "next":
                await self.remind.add_to_remind_next(ctx.author.name)
                await ctx.send(f"You will be pinged when next dlc starts @{ctx.author.name}")
                self.logger.debug(f"Added {ctx.author.name} to next ping list")
                return
            elif msgs[1] == "perma":
                if await self.remind.check_perma_ping(ctx.author.name):
                    await ctx.send(f"You have been removed from perma ping list @{ctx.author.name}")
                    await self.remind.del_perma_ping(ctx.author.name)
                    return
                await ctx.send(f"You will now get pinged every dlc change @{ctx.author.name}")
                self.logger.debug(f"Added {ctx.author.name} to perma ping list")
                await self.remind.add_perma_ping(ctx.author.name)
                return
            else:
                if len(self.remind.remind_next_cur) == 0:
                    await ctx.send(f"There are no dlcs loaded right now")
                    return
                movie = " ".join(msgs[1:]) 
                for x in self.remind.movie_list:
                    if x[0].lower() == movie.lower():
                        if not ctx.author.name in x[2]: x[2].append(ctx.author.name)
                        await ctx.send(f"I will now ping you when {x[0]} starts @{ctx.author.name}")
                        self.logger.debug(f"Added {ctx.author.name} to get pinged for {x[0]}")
                        return
                await ctx.send(f"@{ctx.author.name} Either dlc doesnt exist or incorrect usage, do +remind for examples")
                return
        except IndexError:
            await ctx.send("Usage: +remind {next|perma|<dlc title>}")

    # @commands.command()
    # async def usage(self, ctx:commands.Context):
    #     # print(self.get_command("remind"))
    #     # print(self.get_command("remind").name)
    #     # print(self.get_command("remind").full_name)
    #     # print(self.get_command("remind").aliases)
    #     # print(self.get_command("remind").params)
    #     # print(self.get_command("remind").__dict__)
    #     # print(dir(self.get_command("remind")))
    #     command_list = {}
    #     commands = ['remind', 'suggest']
    #     for command in commands:
    #         command_list[self.get_command(command).name] = [self.get_command(command).aliases]
    #     print(command_list)

    @commands.command()
    async def debug_python(self, ctx: commands.Context):
        if not ctx.author.name == "artifactsection": return
        python_command = " ".join(ctx.message.content.split(" ")[1:])
        row = eval(python_command)
        self.logger.info(f"{row}")
        await ctx.send(f"{row}")

    @commands.command()
    async def debug_sql(self, ctx: commands.Context):
        if not ctx.author.name == "artifactsection": return
        sql_command = " ".join(ctx.message.content.split(" ")[1:])
        row = await self.database.execute(sql_command)
        self.logger.info(f"{row}")

    @commands.command(name="help", aliases=["commands"])
    async def helplist(self, ctx: commands.Context):
        pleb_commands = [
                "remind",
                "suggest"
                ]
        mod_commands = [
                "say",
                "list",
                "trigger",
                "jobs",
                ]
        if ctx.author.name in self.owners:
            await ctx.send(f"Mod commands: {' '.join(pleb_commands) + ' ' + ' '.join(mod_commands)}")
            return
        await ctx.send(f"Pleb commands: {' '.join(pleb_commands)}")

if __name__ == "__main__":
    start_time = time.time()
    bot = Bot()
    bot.run()
