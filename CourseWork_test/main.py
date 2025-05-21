import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import start, schedule, news, questions, help

class UniBotApp:
    def __init__(self, token: str):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()

    def register_handlers(self):
        start.register_handlers_start(self.dp)
        schedule.register_handlers_schedule(self.dp)
        news.register_handlers_news(self.dp)
        questions.register_handlers_questions(self.dp)
        help.register_handlers_help(self.dp)

    async def run(self):
        self.register_handlers()
        await self.dp.start_polling(self.bot)

if __name__ == "__main__":
    async def main():
        app = UniBotApp(token=BOT_TOKEN)
        await app.run()

    asyncio.run(main())