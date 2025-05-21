from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
import datetime

from db import get_connection, get_connection_group

router = Router()

class ScheduleStates(StatesGroup):
    waiting_for_group = State()
    waiting_for_subgroup = State()
    waiting_for_week_type = State()
    waiting_for_day = State()

class GroupStates(StatesGroup):
    waiting_for_new_group = State()

def format_timedelta(td: datetime.timedelta) -> str:
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"

def user_groups_keyboard(groups):
    buttons = []
    for g in groups:
        mark = "✅ " if g.get("selected") else "📚 "
        buttons.append([InlineKeyboardButton(text=f"{mark}{g['group_name']}", callback_data=f"select_group_{g['id']}")])
        buttons.append([InlineKeyboardButton(text=f"❌ Видалити {g['group_name']}", callback_data=f"delete_group_{g['id']}")])
    buttons.append([InlineKeyboardButton(text="➕ Додати групу", callback_data="add_new_group")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def subgroup_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Перша підгрупа", callback_data="subgroup_1")],
        [InlineKeyboardButton(text="2️⃣ Друга підгрупа", callback_data="subgroup_2")],
        [InlineKeyboardButton(text="👥 Вся група", callback_data="subgroup_3")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_group")]
    ])

def week_type_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟣 Парний тиждень", callback_data="week_парний")],
        [InlineKeyboardButton(text="🟠 Непарний тиждень", callback_data="week_непарний")],
        [InlineKeyboardButton(text="⚪️ Щотижня", callback_data="week_щотижня")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_subgroup")]
    ])

def days_inline_keyboard(active_day: int = None):
    days = [
        ("Понеділок", 1), ("Вівторок", 2), ("Середа", 3),
        ("Четвер", 4), ("П’ятниця", 5), ("Субота", 6), ("Неділя", 7)
    ]
    buttons = []
    for i in range(0, 6, 3):
        row = []
        for text, day_num in days[i:i + 3]:
            display_text = f"➡️ {text}" if day_num == active_day else text
            row.append(InlineKeyboardButton(text=display_text, callback_data=f"day_{day_num}"))
        buttons.append(row)
    text, day_num = days[6]
    display_text = f"➡️ {text}" if active_day == 7 else text
    buttons.append([
        InlineKeyboardButton(text=display_text, callback_data=f"day_{day_num}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_week_type")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_user_groups(user_id: int):
    conn = get_connection_group()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, group_name, selected FROM user_groups WHERE user_id = %s", (user_id,))
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

async def add_user_group(user_id: int, group_name: str):
    conn_schedule = get_connection()
    cursor_schedule = conn_schedule.cursor(dictionary=True)
    cursor_schedule.execute("SELECT id FROM `groups` WHERE group_number = %s", (group_name,))
    group_exists = cursor_schedule.fetchone()
    cursor_schedule.close()
    conn_schedule.close()

    if not group_exists:
        return False

    conn = get_connection_group()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM user_groups WHERE user_id = %s AND group_name = %s", (user_id, group_name))
    existing = cursor.fetchone()

    if existing:
        group_id = existing["id"]
        cursor.execute("UPDATE user_groups SET selected = 0 WHERE user_id = %s", (user_id,))
        cursor.execute("UPDATE user_groups SET selected = 1 WHERE id = %s", (group_id,))
    else:
        cursor.execute("UPDATE user_groups SET selected = 0 WHERE user_id = %s", (user_id,))
        cursor.execute("INSERT INTO user_groups (user_id, group_name, selected) VALUES (%s, %s, 1)", (user_id, group_name))

    conn.commit()
    cursor.close()
    conn.close()
    return True


async def delete_user_group(user_id: int, group_id: int):
    conn = get_connection_group()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_groups WHERE id = %s AND user_id = %s", (group_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def format_schedule(schedule_rows, group_number: str, subgroup_text: str, week_type: str) -> str:
    if not schedule_rows:
        return f"📋 Розклад для групи: {group_number}\n\nНа цей день пар не знайдено."

    lines = [
        f"📋 Розклад для групи: {group_number}",
        f"🔹 Тип тижня: {week_type}",
        f"🔹 Підгрупа: {subgroup_text}\n"
    ]

    for row in schedule_rows:
        lesson_num = row.get('lesson_number') or "?"
        subject = row.get('subject_name') or "Н/Д"
        teacher = row.get('teacher_name') or "Н/Д"
        location = row.get('location_name') or "Н/Д"
        start = format_timedelta(row['start_time']) if row.get('start_time') else "??:??"
        end = format_timedelta(row['end_time']) if row.get('end_time') else "??:??"

        lines.append(f"{lesson_num}⃣ {subject}")
        lines.append(f"🎓 {teacher} | 📍 {location}")
        lines.append(f"🕓 {start} – {end}")
        lines.append("➖" * 10)

    return "\n".join(lines)

async def show_schedule(callback: types.CallbackQuery, state: FSMContext, day: int):
    data = await state.get_data()
    group_db_id = data.get("selected_group_id")
    week_type = data.get("selected_week_type", "щотижня")
    subgroup_id = int(data.get("selected_subgroup", 3))
    keyboard = days_inline_keyboard(active_day=day)

    user_groups = await get_user_groups(callback.from_user.id)
    group_name = next((g["group_name"] for g in user_groups if g["id"] == group_db_id), None)

    if not group_name:
        await callback.message.edit_text("Не вдалося знайти номер групи.")
        return

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM `groups` WHERE group_number = %s", (group_name,))
        group = cursor.fetchone()
        if not group:
            await callback.message.edit_text("Групу не знайдено в розкладі.")
            return
        schedule_group_id = group["id"]
    except Exception as e:
        print(f"Помилка при отриманні group_id: {e}")
        await callback.message.edit_text("Помилка під час доступу до розкладу.")
        return
    finally:
        cursor.close()
        conn.close()

    if day == 7:
        text = "*Неділя*\nСьогодні вихідний ☀️"
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer("Цей день вже відкритий ✅", show_alert=False)
            else:
                raise
        else:
            await callback.answer()
        return

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.day_of_week, subj.subject_name, t.teacher_name, l.location_name,
                   les.start_time, les.end_time, les.lesson_number, w.week_type
            FROM Schedule s
            LEFT JOIN Subjects subj ON s.subject_id = subj.id
            LEFT JOIN Teachers t ON s.teacher_id = t.id
            LEFT JOIN Locations l ON s.location_id = l.id
            LEFT JOIN Lessons les ON s.lesson_id = les.id
            LEFT JOIN Weeks w ON s.week_id = w.id
            WHERE s.group_id = %s AND s.day_of_week = %s AND s.subgroup_id IN (%s, 3)
              AND (w.week_type = %s OR w.week_type = 'щотижня')
            ORDER BY les.start_time
        """, (schedule_group_id, day, subgroup_id, week_type))
        schedule_rows = cursor.fetchall()
    except Exception as e:
        print(f"DB error: {e}")
        schedule_rows = []
    finally:
        cursor.close()
        conn.close()

    subgroup_text = {
        1: "Перша підгрупа",
        2: "Друга підгрупа",
        3: "Вся група"
    }.get(subgroup_id, "Невідома")


    text = format_schedule(schedule_rows, group_name, subgroup_text, week_type)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Цей день вже відкритий ✅", show_alert=False)
        else:
            raise
    else:
        await callback.answer()


@router.message(Command("schedule"))
@router.callback_query(lambda c: c.data == "menu:schedule")
async def cmd_schedule(event: types.Message | types.CallbackQuery, state: FSMContext):
    if isinstance(event, types.CallbackQuery):
        user_id = event.from_user.id
        send = event.message.answer
    else:
        user_id = event.from_user.id
        send = event.answer

    groups = await get_user_groups(user_id)
    if not groups:
        await send("У вас немає жодної групи. Введіть номер групи — це має бути комбінація з трьох цифр, наприклад: 209")
        await state.set_state(GroupStates.waiting_for_new_group)
    else:
        selected = next((g for g in groups if g["selected"]), None)
        if selected:
            await state.update_data(selected_group_id=selected["id"])
            await send(f"Ваша група: {selected['group_name']}\nОберіть підгрупу:", reply_markup=subgroup_keyboard())
            await state.set_state(ScheduleStates.waiting_for_subgroup)
        else:
            await send("Оберіть групу:", reply_markup=user_groups_keyboard(groups))
            await state.set_state(ScheduleStates.waiting_for_group)


@router.message(StateFilter(GroupStates.waiting_for_new_group))
async def new_group_name(message: types.Message, state: FSMContext):
    group_name = message.text.strip()
    groups = await get_user_groups(message.from_user.id)

    result = await add_user_group(message.from_user.id, group_name)
    if not result:
        await message.answer(
            "❌ Такої групи не знайдено в базі даних.\n"
            "🔔 Перевірте правильність написання або зверніться до адміна.\n\n"
            "Оберіть іншу групу:",
            reply_markup=user_groups_keyboard(groups))

        return

    await message.answer(f"✅ Групу *{group_name}* додано та вибрано як основну", parse_mode="Markdown")
    await cmd_schedule(message, state)

@router.callback_query(F.data.startswith("select_group_"))
async def select_group(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id

    conn = get_connection_group()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("UPDATE user_groups SET selected = 0 WHERE user_id = %s", (user_id,))
    cursor.execute("UPDATE user_groups SET selected = 1 WHERE id = %s AND user_id = %s", (group_id, user_id))
    conn.commit()

    cursor.execute("SELECT group_name FROM user_groups WHERE id = %s", (group_id,))
    group = cursor.fetchone()
    cursor.close()
    conn.close()

    await state.update_data(selected_group_id=group_id)
    await callback.message.edit_text(f"Ваша група: {group['group_name']}\nОберіть підгрупу:", reply_markup=subgroup_keyboard())
    await state.set_state(ScheduleStates.waiting_for_subgroup)
    await callback.answer()

@router.callback_query(F.data.startswith("delete_group_"))
async def delete_group_callback(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    await delete_user_group(user_id, group_id)
    await callback.answer("Групу видалено.")
    groups = await get_user_groups(user_id)
    if groups:
        await callback.message.edit_text("Оберіть групу:", reply_markup=user_groups_keyboard(groups))
        await state.set_state(ScheduleStates.waiting_for_group)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Додати групу", callback_data="add_new_group")]
        ])
        await callback.message.edit_text("У вас немає жодної групи. Додайте нову _(Це має бути комбінація з трьох цифр, наприклад: 209)_",parse_mode="Markdown", reply_markup=kb)
        await state.set_state(GroupStates.waiting_for_new_group)

@router.callback_query(F.data == "add_new_group")
async def add_group(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введіть номер нової групи:")
    await state.set_state(GroupStates.waiting_for_new_group)
    await callback.answer()

@router.callback_query(F.data.startswith("subgroup_"))
async def select_subgroup(callback: types.CallbackQuery, state: FSMContext):
    subgroup_id = callback.data.split("_")[1]
    await state.update_data(selected_subgroup=subgroup_id)
    await callback.message.edit_text("Оберіть тип тижня:", reply_markup=week_type_keyboard())
    await state.set_state(ScheduleStates.waiting_for_week_type)
    await callback.answer()

@router.callback_query(F.data.startswith("week_"))
async def select_week(callback: types.CallbackQuery, state: FSMContext):
    week_type = callback.data.split("_")[1]
    await state.update_data(selected_week_type=week_type)
    await callback.message.edit_text("Оберіть день тижня:", reply_markup=days_inline_keyboard())
    await state.set_state(ScheduleStates.waiting_for_day)
    await callback.answer()

@router.callback_query(F.data.startswith("day_"))
async def select_day(callback: types.CallbackQuery, state: FSMContext):
    day = int(callback.data.split("_")[1])
    await show_schedule(callback, state, day)

@router.callback_query(F.data == "back_to_subgroup")
async def back_to_subgroup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Оберіть підгрупу:", reply_markup=subgroup_keyboard())
    await state.set_state(ScheduleStates.waiting_for_subgroup)
    await callback.answer()

@router.callback_query(F.data == "back_to_group")
async def back_to_group_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    groups = await get_user_groups(user_id)

    if not groups:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Додати групу", callback_data="add_new_group")]
        ])
        await callback.message.edit_text("У вас немає жодної групи. Додайте нову _(Це має бути комбінація з трьох цифр, наприклад: 101)_ :", parse_mode="Markdown",reply_markup=kb)
        await state.set_state(GroupStates.waiting_for_new_group)
    else:
        kb = user_groups_keyboard(groups)
        selected_group = next((g for g in groups if int(g.get("selected", 0)) == 1), None)

        if selected_group:
            text = f"Ваша обрана група: {selected_group['group_name']}\nОберіть групу або змініть вибір:"
        else:
            text = "Оберіть групу:"

        await callback.message.edit_text(text, reply_markup=kb)
        await state.set_state(ScheduleStates.waiting_for_group)

    await callback.answer()


@router.callback_query(F.data == "back_to_week_type")
async def back_to_week(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Оберіть тип тижня:", reply_markup=week_type_keyboard())
    await state.set_state(ScheduleStates.waiting_for_week_type)
    await callback.answer()

def register_handlers_schedule(dp):
    dp.include_router(router)
