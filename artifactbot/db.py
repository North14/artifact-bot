import aiosqlite

class Database:
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "./data/artifact.db3"
        self.build_path = "./build.sql"

    async def connect(self):
        self.db = await aiosqlite.connect(self.db_path)
        await self.executescript(self.build_path)
        await self.commit()

    async def disconnect(self):
        await self.db.commit()
        await self.db.close()

    async def commit(self):
        await self.db.commit()

    async def record(self, sql, *values):
        cur = await self.db.execute(sql, tuple(values))
        return await cur.fetchone()

    async def records(self, sql, *values):
        cur = await self.db.execute(sql, tuple(values))
        return await cur.fetchall()

    async def execute(self, sql, *values):
        cur = await self.db.execute(sql, tuple(values))
        return cur.rowcount
    
    async def executescript(self, path):
        with open(path, "r", encoding="utf-8") as script:
            await self.db.executescript(script.read())

