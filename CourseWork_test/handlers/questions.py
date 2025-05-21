from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import ADMIN_CHAT_ID

class QuestionStates(StatesGroup):
    waiting_for_question = State()

class AdminStates(StatesGroup):
    waiting_for_answer = State()

class QuestionsHandler:
    def __init__(self):
        self.router = Router()
        self.admin_reply_targets = {}

        self.router.message.register(self.ask_admin_command, Command("questions"))
        self.router.message.register(self.handle_question, QuestionStates.waiting_for_question)
        self.router.callback_query.register(self.admin_choose_user, F.data.startswith("answer_"))
        self.router.message.register(self.handle_admin_answer, AdminStates.waiting_for_answer)

    def get_router(self):
        return self.router

    async def ask_admin_command(self, message: Message, state: FSMContext):
        await state.set_state(QuestionStates.waiting_for_question)
        await message.answer("📩 Напишіть ваше питання для адміна:")

    async def handle_question(self, message: Message, bot: Bot, state: FSMContext):
        user_id = message.from_user.id
        username = message.from_user.username or "Без імені"
        text = message.text

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Відповісти", callback_data=f"answer_{user_id}")]
        ])

        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"❓ Питання від @{username} (ID: {user_id}):\n\n{text}",
            reply_markup=keyboard
        )

        await message.answer("✅ Ваше питання надіслано адміну!")
        await state.clear()

    async def admin_choose_user(self, callback: CallbackQuery, state: FSMContext):
        user_id = int(callback.data.split("_")[1])
        admin_id = callback.from_user.id

        self.admin_reply_targets[admin_id] = user_id

        await state.set_state(AdminStates.waiting_for_answer)
        await callback.message.answer(f"✍️ Введіть вашу відповідь для користувача з ID {user_id}:")
        await callback.answer()

    async def handle_admin_answer(self, message: Message, bot: Bot, state: FSMContext):
        admin_id = message.from_user.id
        user_id = self.admin_reply_targets.get(admin_id)

        if not user_id:
            await message.answer("❌ Немає активного користувача для відповіді.")
            return

        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"📩 Відповідь адміна:\n\n{message.text}"
            )
            await message.answer("✅ Ваша відповідь надіслана користувачу.")
        except Exception as e:
            await message.answer(f"❌ Помилка при надсиланні відповіді: {e}")

        await state.clear()
        del self.admin_reply_targets[admin_id]

def register_handlers_questions(dp):
    handler = QuestionsHandler()
    dp.include_router(handler.get_router())

questions_handler_instance = QuestionsHandler()