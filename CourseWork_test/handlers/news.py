from aiogram import Router, types, F
from config import CHANNEL_ID


class NewsHandler:
    def __init__(self):
        self.router = Router()
        self.last_post = None

        self.router.message.register(self.catch_channel_post, F.chat.id == CHANNEL_ID)
        self.router.message.register(self.catch_forwarded, F.forward_from_chat)
        self.router.message.register(self.send_last_news, F.text == "/news")

    def get_router(self):
        return self.router

    async def catch_channel_post(self, message: types.Message):
        self.last_post = message

    async def catch_forwarded(self, message: types.Message):
        if message.forward_from_chat.id == CHANNEL_ID:
            self.last_post = message

    async def send_last_news(self, message: types.Message):
        if self.last_post is None:
            await message.answer("Поки немає нових новин :(")
            return

        if self.last_post.photo:
            caption = self.last_post.caption or ""
            await message.answer_photo(self.last_post.photo[-1].file_id, caption=caption)
            if self.last_post.text and self.last_post.text != caption:
                await message.answer(self.last_post.text)

        elif self.last_post.video:
            caption = self.last_post.caption or ""
            await message.answer_video(self.last_post.video.file_id, caption=caption)
            if self.last_post.text and self.last_post.text != caption:
                await message.answer(self.last_post.text)

        elif self.last_post.text:
            await message.answer(self.last_post.text)
        else:
            await message.answer("Останній пост з каналу, тип контенту не підтримується :(")

news_handler_instance = NewsHandler()

def register_handlers_news(dp):
    dp.include_router(news_handler_instance.get_router())
