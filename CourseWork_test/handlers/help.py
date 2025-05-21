from aiogram import Router, types
from aiogram.filters import Command

class HelpHandler:
    def __init__(self):
        self.router = Router()
        self.router.message.register(self.cmd_help, Command("help"))

    async def cmd_help(self, message: types.Message):
        await message.answer(
            "🆘 *Довідка*\n\n"
            "📍 /start — команда, що відкриє головне меню з усіма можливостями бота\n"
            "📅 *Розклад* — натисни кнопку «Розклад», щоб:\n"
            "   └ 🔹 Вибрати або додати\\видалити  групу \n_(Додані групи зберігаються)_\n"
            "   └ 🔸 Обрати підгрупу (1, 2 або вся група)\n"
            "   └ 🔄 Обрати тип тижня (парний / непарний / щотижня)\n"
            "   └ 🗓️ Переглянути розклад на будь-який день тижня\n\n"
            "📰 *Що нового в університеті?* — дізнавайся останні новини університету та не тільки\n"
            "❓ *Питання до адміна* — маєш питання чи щось не працює? Просто натисни кнопку та задай питання адміну напряму 📩\n\n"
            "📌 Якщо твоя група не знайдена — повідом про це — її додамо!\n\n"
            "💙 Дякую, що користуєшся ботом!! :)",
            parse_mode="Markdown"
        )

    def register(self, dp):
        dp.include_router(self.router)

help_handler_instance = HelpHandler()

def register_handlers_help(dp):
    help_handler_instance.register(dp)
