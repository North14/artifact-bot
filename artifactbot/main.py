from twitchio.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import re
import sys

from remind import Remind
from db import Database
from suggest import Suggest
from settings import *

def parse_movie_list(movie_list):
    movie_list = re.sub("^.* UTC\+2] ", '', str(movie_list))
    movie_list = re.split(" ⏩ ", str(movie_list))
    list1 = []
    for x in movie_list:
        time = re.search(r"([01]?[0-9]|2[0-3]):[0-5][0-9]", x).group()
        movie = re.sub(r" \(([01]?[0-9]|2[0-3]):[0-5][0-9]\)", '', x)
        list1.append([movie, time])
    return list1

class Bot(commands.Bot):

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scheduler.configure(timezone='cet')
        self.remind = Remind(self)
        self.database = Database(self)
        self.suggest = Suggest(self)
        super().__init__(token=token, prefix=prefix, initial_channels=initial_channels)

    async def event_ready(self):
        print(f'Logged in as | {self.nick}')
        await self.database.connect()
        print("Database connected")
        self.scheduler.start()
        print("Scheduler started")
        self.channel: twitchio.Channel = self.get_channel(
            next(iter(initial_channels))
        )
        await self.channel.send("Bot is now online!")

    @commands.command()
    async def clear(self, ctx: commands.Context):
        if not ctx.author.name in owners: return
        self.remind.clear_remind_next_cur()
        await ctx.send("List cleared")

    @commands.command()
    async def jobs(self, ctx: commands.Context):
        if not ctx.author.name in owners: return
        await ctx.send(f"There are ({len(self.scheduler.get_jobs()):,} jobs in queue")

    @commands.command()
    async def pings(self, ctx: commands.Context):
        if not ctx.author.name in owners: return
        await ctx.send(f"There are {len(self.remind.remind_next)} bajs waiting for ping")

    @commands.command()
    async def shutdown(self, ctx: commands.Context):
        if not ctx.author.name in owners: return
        self.scheduler.shutdown()
        await self.database.disconnect()
        sys.exit(0)

    @commands.command()
    async def ping(self, ctx: commands.Context):
        cur_time = datetime.now().strftime("%H:%M")
        await ctx.send(f"pong : {cur_time}")

    @commands.command()
    async def trigger(self, ctx: commands.Context):
        if not ctx.author.name in owners: return
        await self.remind.send_remind_next()

    @commands.command()
    async def say(self, ctx: commands.Context):
        if not ctx.author.name in owners: return
        await ctx.send(" ".join(ctx.message.content.split(" ")[1:]))
    
    @commands.command()
    async def mod(self, ctx: commands.Context):
        msgs = ctx.message.content.split(" ")
        if msgs[1]:
            await ctx.send(f"/ /mod {msgs[1]} Clueless")

    @commands.command(name="time", aliases=["list"])
    async def parse_list(self, ctx: commands.Context):
        # TODO if movies already in list, update times
        if not ctx.author.name in owners: return
        msgs = ctx.message.content
        movie_list = " ".join(str(msgs).split(" ")[1:])
        self.remind.clear_remind_next_cur()
        movies = parse_movie_list(movie_list)
        #  [["movie1", "12:34"], ["movie2", "23:12"]]
        already_played = True
        cur_time = datetime.now().strftime("%H:%M")
        for x in movies:
            if already_played:
                if datetime.strptime(cur_time, "%H:%M") < datetime.strptime(x[1], "%H:%M"):
                    already_played = False
                else:
                    print(f"{x[0]} already played")
                    continue
            x.append([])
            print(f"Adding job: {x}")
            self.remind.movie_list.append(x)
            hour, minute = x[1].split(':')
            self.remind.add_to_remind_next_cur(hour, minute)
        print(self.remind.movie_list)
        await ctx.send(f"{len(self.scheduler.get_jobs()):,} jobs loaded")

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
        if not ctx.author.name in owners: return
        await self.suggest.print_suggestions()

    @commands.command(name="remind", aliases=["remindme"])
    async def reminder(self, ctx: commands.Context):
        msgs = ctx.message.content.split(" ")
        print(msgs)
        try:
            if msgs[1] == "next":
                await self.remind.add_to_remind_next(ctx.author.name)
                await ctx.send(f"You will be pinged when next dlc starts @{ctx.author.name}")
                print(f"Added {ctx.author.name} to next ping list")
                return
            elif msgs[1] == "perma":
                if await self.remind.check_perma_ping(ctx.author.name):
                    await ctx.send(f"You have been removed from perma ping list @{ctx.author.name}")
                    await self.remind.del_perma_ping(ctx.author.name)
                    return
                await ctx.send(f"You will now get pinged every dlc change @{ctx.author.name}")
                print(f"Added {ctx.author.name} to perma ping list")
                await self.remind.add_perma_ping(ctx.author.name)
                return
            else:
                if len(self.scheduler.get_jobs()) == 0:
                    await ctx.send(f"There are no dlcs loaded right now")
                    return
                movie = " ".join(msgs[1:]) 
                for x in self.remind.movie_list:
                    if x[0] == movie:
                        if not ctx.author.name in x[2]: x[2].append(ctx.author.name)
                        await ctx.send(f"I will now ping you when {movie} starts @{ctx.author.name}")
                        print(f"Added {ctx.author.name} to get pinged for {movie}")
                        return
                await ctx.send(f"@{ctx.author.name} Either dlc doesnt exist or incorrect usage, do +remind for examples")
                return
        except IndexError:
            await ctx.send("Usage: +remind {next|perma|<dlc title>}")

    @commands.command()
    async def test(self, ctx:commands.Context):
        table = await self.remind.get_perma_pings()
        print(table)

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
                "pings",
                ]
        if ctx.author.name in owners:
            await ctx.send(f"Mod commands: {' '.join(pleb_commands) + ' ' + ' '.join(mod_commands)}")
            return
        await ctx.send(f"Pleb commands: {' '.join(pleb_commands)}")

if __name__ == "__main__":
    bot = Bot()
    bot.run()
