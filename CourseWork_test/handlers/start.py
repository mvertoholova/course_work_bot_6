from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from handlers.help import help_handler_instance
from handlers.news import news_handler_instance
from handlers.questions import questions_handler_instance
from handlers.schedule import cmd_schedule


class StartHandler:
    def __init__(self):
        self.router = Router()
        self.register_commands()

    def main_menu_keyboard(self):
        return types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="📅 Розклад", callback_data="menu:schedule"),
                types.InlineKeyboardButton(text="📰 Що нового в університеті?", callback_data="menu:news"),
            ],
            [
                types.InlineKeyboardButton(text="❓ Питання до адміна", callback_data="menu:questions"),
            ],
            [
                types.InlineKeyboardButton(text="🆘 Довідка", callback_data="menu:help")
            ]
        ])

    def register_commands(self):
        @self.router.message(Command("start"))
        async def cmd_start(message: types.Message, state: FSMContext):
            await state.clear()
            user_fullname = message.from_user.full_name
            await message.answer(
                f"Вітаю, {user_fullname}!! 👋\n\n"
                "Я — твій помічник-бот, створений для того, щоб зробити твою взаємодію з розкладом зручним, адже в мене ти завжди можеш дізнатись, які в тебе пари протягом тижня 😈 \n\n"
                "Потрібна допомога з командами?? Просто відправ мені /help\n\n"
                "Обери, що тебе цікавить нижче ⬇️",
                reply_markup=self.main_menu_keyboard()
            )

        @self.router.callback_query(lambda c: c.data and c.data.startswith("menu:"))
        async def global_callback_handler(callback: types.CallbackQuery, state: FSMContext):
            data = callback.data
            await state.clear()
            await callback.answer()

            if data == "menu:schedule":
                await cmd_schedule(callback, state)
            elif data == "menu:news":
                await news_handler_instance.send_last_news(callback.message)
            elif data == "menu:questions":
                await questions_handler_instance.ask_admin_command(callback.message, state)
            elif data == "menu:help":
                await help_handler_instance.cmd_help(callback.message)

    def register(self, dp):
        dp.include_router(self.router)

def register_handlers_start(dp):
    start_handler = StartHandler()
    start_handler.register(dp)
