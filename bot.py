import asyncio
import os
import html
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv


# =========================================================
# НАСТРОЙКИ
# =========================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DB_FILE = "sergey_project.db"


# =========================================================
# БАЗА ДАННЫХ
# =========================================================

def get_db():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            username TEXT,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.commit()
    db.close()


def save_user(user):
    db = get_db()

    db.execute("""
        INSERT INTO users (user_id, full_name, username)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            full_name = excluded.full_name,
            username = excluded.username
    """, (
        user.id,
        user.full_name,
        user.username or ""
    ))

    db.commit()
    db.close()


def save_order(user, order_text):
    db = get_db()

    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO orders (
            user_id,
            full_name,
            username,
            text
        )
        VALUES (?, ?, ?, ?)
    """, (
        user.id,
        user.full_name,
        user.username or "",
        order_text
    ))

    order_id = cursor.lastrowid

    db.commit()
    db.close()

    return order_id


def get_users():
    db = get_db()

    users = db.execute("""
        SELECT *
        FROM users
        ORDER BY created_at DESC
    """).fetchall()

    db.close()

    return users


def get_orders(limit=None):
    db = get_db()

    if limit:
        orders = db.execute("""
            SELECT *
            FROM orders
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()
    else:
        orders = db.execute("""
            SELECT *
            FROM orders
            ORDER BY id DESC
        """).fetchall()

    db.close()

    return orders


def get_user_count():
    db = get_db()

    count = db.execute("""
        SELECT COUNT(*)
        FROM users
    """).fetchone()[0]

    db.close()

    return count


def get_order_count():
    db = get_db()

    count = db.execute("""
        SELECT COUNT(*)
        FROM orders
    """).fetchone()[0]

    db.close()

    return count


# =========================================================
# СОСТОЯНИЯ
# =========================================================

class OrderState(StatesGroup):
    waiting_for_order = State()
    confirmation = State()


class ContactState(StatesGroup):
    waiting_for_message = State()


class AdminReplyState(StatesGroup):
    waiting_for_reply = State()


class BroadcastState(StatesGroup):
    waiting_for_message = State()
    confirmation = State()


# =========================================================
# ПРОВЕРКА АДМИНА
# =========================================================

def is_admin(user_id):
    return user_id == ADMIN_ID


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

def main_menu():
    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="📚 Оформить заявку",
        callback_data="order"
    )

    keyboard.button(
        text="📦 Что входит в работу",
        callback_data="included"
    )

    keyboard.button(
        text="⭐ Почему выбирают нас",
        callback_data="why"
    )

    keyboard.button(
        text="💬 Отзывы",
        url="https://t.me/projectsergey1ak"
    )

    keyboard.button(
        text="📞 Связаться",
        callback_data="contact"
    )

    keyboard.adjust(1)

    return keyboard.as_markup()


# =========================================================
# НАЗАД В ГЛАВНОЕ МЕНЮ
# =========================================================

def back_to_menu():
    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="🏠 Вернуться в главное меню",
        callback_data="back"
    )

    return keyboard.as_markup()


# =========================================================
# КНОПКА НАЗАД ПРИ ЗАЯВКЕ
# =========================================================

def order_back_button():
    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="🏠 Назад в главное меню",
        callback_data="back"
    )

    return keyboard.as_markup()


# =========================================================
# ПОДТВЕРЖДЕНИЕ ЗАЯВКИ
# =========================================================

def order_confirmation():
    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="✅ Отправить заявку",
        callback_data="send_order"
    )

    keyboard.button(
        text="✏️ Заполнить заново",
        callback_data="edit_order"
    )

    keyboard.button(
        text="❌ Отменить",
        callback_data="cancel_order"
    )

    keyboard.adjust(1)

    return keyboard.as_markup()


# =========================================================
# КНОПКА ОТВЕТА АДМИНА
# =========================================================

def admin_reply_button(user_id):
    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="💬 Ответить пользователю",
        callback_data=f"reply_{user_id}"
    )

    return keyboard.as_markup()


# =========================================================
# АДМИН-ПАНЕЛЬ
# =========================================================

def admin_menu():
    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="📊 Статистика",
        callback_data="admin_stats"
    )

    keyboard.button(
        text="📢 Рассылка",
        callback_data="admin_broadcast"
    )

    keyboard.button(
        text="👥 Пользователи",
        callback_data="admin_users"
    )

    keyboard.button(
        text="📋 Заявки",
        callback_data="admin_orders"
    )

    keyboard.button(
        text="❌ Закрыть",
        callback_data="admin_close"
    )

    keyboard.adjust(2, 2, 1)

    return keyboard.as_markup()


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):

    await state.clear()

    save_user(message.from_user)

    text = """
🎓 <b>SERGEY PROJECT</b>

Привет! 👋

Если тебе нужен индивидуальный учебный проект, презентация или материалы для защиты — ты по адресу.

Здесь всё просто: выбираешь нужный раздел, оставляешь заявку или задаёшь вопрос.

<b>Что здесь можно сделать?</b>

📚 Оформить заявку
📦 Узнать, что входит в работу
⭐ Посмотреть преимущества
💬 Ознакомиться с отзывами
📞 Связаться со мной

🤝 Общаемся на «ты», без лишней официальности.

👇 Выбирай нужный раздел:
"""

    await message.answer(
        text,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# =========================================================
# ADMIN
# =========================================================

@dp.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext):

    if not is_admin(message.from_user.id):
        await message.answer(
            "🙂 У тебя нет доступа к этой команде."
        )
        return

    await state.clear()

    await message.answer(
        """
🔐 <b>АДМИН-ПАНЕЛЬ</b>

Добро пожаловать в панель управления SERGEY PROJECT.

👇 Выбирай нужный раздел:
""",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )


# =========================================================
# СТАТИСТИКА
# =========================================================

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    users = get_user_count()
    orders = get_order_count()

    average = round(orders / users, 2) if users else 0

    text = f"""
📊 <b>СТАТИСТИКА</b>

👥 Пользователей: <b>{users}</b>

📚 Всего заявок: <b>{orders}</b>

📈 Заявок на пользователя: <b>{average}</b>
"""

    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="◀️ Админ-панель",
        callback_data="admin_back"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ПОЛЬЗОВАТЕЛИ
# =========================================================

@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    users = get_users()

    text = f"""
👥 <b>ПОЛЬЗОВАТЕЛИ</b>

Сейчас в базе:

<b>{len(users)}</b> пользователей.

Все пользователи сохраняются автоматически после запуска бота.
"""

    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="📢 Сделать рассылку",
        callback_data="admin_broadcast"
    )

    keyboard.button(
        text="◀️ Админ-панель",
        callback_data="admin_back"
    )

    keyboard.adjust(1)

    await callback.message.edit_text(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ЗАЯВКИ
# =========================================================

@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    orders = get_orders(10)

    if not orders:
        text = """
📋 <b>ЗАЯВКИ</b>

Пока заявок нет.
"""

    else:

        text = "📋 <b>ПОСЛЕДНИЕ ЗАЯВКИ</b>\n\n"

        for order in orders:

            username = (
                f"@{order['username']}"
                if order["username"]
                else "не указан"
            )

            safe_name = html.escape(order["full_name"])
            safe_username = html.escape(username)
            safe_text = html.escape(order["text"])

            text += f"""
<b>Заявка №{order['id']}</b>

👤 {safe_name}
🔗 {safe_username}
🆔 <code>{order['user_id']}</code>

📄 {safe_text}

━━━━━━━━━━━━━━
"""

    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="◀️ Админ-панель",
        callback_data="admin_back"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# РАССЫЛКА
# =========================================================

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    await state.set_state(
        BroadcastState.waiting_for_message
    )

    await callback.message.edit_text(
        """
📢 <b>РАССЫЛКА</b>

Отправь следующим сообщением текст, который хочешь отправить пользователям.

После этого я покажу предпросмотр.

❌ Чтобы отменить — напиши <b>отмена</b>.
""",
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ТЕКСТ РАССЫЛКИ
# =========================================================

@dp.message(BroadcastState.waiting_for_message)
async def receive_broadcast(
    message: Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    if not message.text:
        await message.answer(
            "🙂 Для рассылки нужен обычный текст."
        )
        return

    if message.text.lower() == "отмена":

        await state.clear()

        await message.answer(
            "❌ Рассылка отменена.",
            reply_markup=admin_menu()
        )

        return

    await state.update_data(
        broadcast_text=message.text
    )

    users_count = get_user_count()

    safe_text = html.escape(message.text)

    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="📢 Отправить всем",
        callback_data="confirm_broadcast"
    )

    keyboard.button(
        text="❌ Отменить",
        callback_data="cancel_broadcast"
    )

    keyboard.adjust(1)

    await state.set_state(
        BroadcastState.confirmation
    )

    await message.answer(
        f"""
📢 <b>ПРЕДПРОСМОТР</b>

━━━━━━━━━━━━━━

{safe_text}

━━━━━━━━━━━━━━

👥 Получателей: <b>{users_count}</b>

Отправить сообщение всем?
""",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )


# =========================================================
# ПОДТВЕРЖДЕНИЕ РАССЫЛКИ
# =========================================================

@dp.callback_query(
    BroadcastState.confirmation,
    F.data == "confirm_broadcast"
)
async def confirm_broadcast(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user.id):
        return

    data = await state.get_data()

    broadcast_text = data.get(
        "broadcast_text",
        ""
    )

    users = get_users()

    await callback.message.edit_text(
        "📢 <b>Рассылка началась...</b>\n\n"
        "Пожалуйста, подожди.",
        parse_mode="HTML"
    )

    success = 0
    failed = 0

    safe_text = html.escape(broadcast_text)

    for user in users:

        user_id = user["user_id"]

        if user_id == ADMIN_ID:
            continue

        try:

            await bot.send_message(
                user_id,
                f"""
📢 <b>SERGEY PROJECT</b>

{safe_text}
""",
                parse_mode="HTML"
            )

            success += 1

            await asyncio.sleep(0.05)

        except Exception:
            failed += 1

    await state.clear()

    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="🔐 Админ-панель",
        callback_data="admin_back"
    )

    await callback.message.edit_text(
        f"""
✅ <b>РАССЫЛКА ЗАВЕРШЕНА</b>

📨 Успешно отправлено: <b>{success}</b>

❌ Не удалось отправить: <b>{failed}</b>
""",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ОТМЕНА РАССЫЛКИ
# =========================================================

@dp.callback_query(
    BroadcastState.confirmation,
    F.data == "cancel_broadcast"
)
async def cancel_broadcast(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user.id):
        return

    await state.clear()

    await callback.message.edit_text(
        "❌ <b>Рассылка отменена.</b>",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ОФОРМЛЕНИЕ ЗАЯВКИ
# =========================================================

@dp.callback_query(F.data == "order")
async def order(
    callback: CallbackQuery,
    state: FSMContext
):

    save_user(callback.from_user)

    await state.set_state(
        OrderState.waiting_for_order
    )

    text = """
📚 <b>ОФОРМЛЕНИЕ ЗАЯВКИ</b>

Давай быстро разберёмся, что тебе нужно.

Отправь одним сообщением:

🎓 Класс / курс
📖 Предмет
📝 Тема проекта
📅 Когда нужна работа
📦 Что тебе требуется

<b>Например:</b>

10 класс
Физика
Электромагнитная индукция
Нужно к 25 августа
Проект + презентация + речь

После этого я покажу тебе заявку перед отправкой.

⚠️ Заявка никуда не отправится, пока ты сам не нажмёшь «Отправить заявку».
"""

    await callback.message.edit_text(
        text,
        reply_markup=order_back_button(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ПОЛУЧЕНИЕ ЗАЯВКИ
# =========================================================

@dp.message(OrderState.waiting_for_order)
async def receive_order(
    message: Message,
    state: FSMContext
):

    save_user(message.from_user)

    if not message.text:

        await message.answer(
            "🙂 Отправь информацию обычным текстовым сообщением.",
            reply_markup=order_back_button()
        )

        return

    await state.update_data(
        order_text=message.text
    )

    user = message.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "не указан"
    )

    safe_name = html.escape(user.full_name)
    safe_username = html.escape(username)
    safe_order = html.escape(message.text)

    preview = f"""
📋 <b>ПРОВЕРЬ ЗАЯВКУ</b>

👤 Имя: {safe_name}
🔗 Username: {safe_username}

━━━━━━━━━━━━━━

📄 <b>Данные проекта:</b>

{safe_order}

━━━━━━━━━━━━━━

Всё верно?

Если всё правильно — нажми «Отправить заявку».

⚠️ До этого момента заявка не отправлена.
"""

    await state.set_state(
        OrderState.confirmation
    )

    await message.answer(
        preview,
        reply_markup=order_confirmation(),
        parse_mode="HTML"
    )


# =========================================================
# ОТПРАВКА ЗАЯВКИ
# =========================================================

@dp.callback_query(
    OrderState.confirmation,
    F.data == "send_order"
)
async def send_order(
    callback: CallbackQuery,
    state: FSMContext
):

    data = await state.get_data()

    order_text = data.get(
        "order_text",
        "Информация не указана"
    )

    user = callback.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "не указан"
    )

    safe_name = html.escape(user.full_name)
    safe_username = html.escape(username)
    safe_order = html.escape(order_text)

    order_id = save_order(
        user,
        order_text
    )

    admin_text = f"""
📥 <b>НОВАЯ ЗАЯВКА №{order_id}</b>

👤 Клиент: {safe_name}
🔗 Username: {safe_username}
🆔 Telegram ID: <code>{user.id}</code>

━━━━━━━━━━━━━━

📄 <b>Заявка:</b>

{safe_order}
"""

    await bot.send_message(
        ADMIN_ID,
        admin_text,
        parse_mode="HTML",
        reply_markup=admin_reply_button(user.id)
    )

    await state.clear()

    text = """
✅ <b>ЗАЯВКА ОТПРАВЛЕНА!</b>

Готово! Я получил твою заявку.

Скоро свяжусь с тобой, чтобы обсудить детали проекта, сроки и всё необходимое.

🤝 Спасибо, что обратился в SERGEY PROJECT!
"""

    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )

    await callback.answer(
        "Заявка отправлена! ✅"
    )


# =========================================================
# ЗАПОЛНИТЬ ЗАНОВО
# =========================================================

@dp.callback_query(
    OrderState.confirmation,
    F.data == "edit_order"
)
async def edit_order(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        OrderState.waiting_for_order
    )

    text = """
✏️ <b>ЗАПОЛНИМ ЗАНОВО</b>

Отправь одним сообщением:

🎓 Класс / курс
📖 Предмет
📝 Тема проекта
📅 Когда нужна работа
📦 Что тебе нужно
"""

    await callback.message.edit_text(
        text,
        reply_markup=order_back_button(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ОТМЕНА ЗАЯВКИ
# =========================================================

@dp.callback_query(
    OrderState.confirmation,
    F.data == "cancel_order"
)
async def cancel_order(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.message.edit_text(
        """
❌ <b>ЗАЯВКА ОТМЕНЕНА</b>

Ничего страшного 🙂

Если захочешь оформить её позже, просто вернись в главное меню.
""",
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )

    await callback.answer(
        "Заявка отменена"
    )


# =========================================================
# ЧТО ВХОДИТ В РАБОТУ
# =========================================================

@dp.callback_query(F.data == "included")
async def included(callback: CallbackQuery):

    save_user(callback.from_user)

    text = """
📦 <b>ЧТО МОЖНО ПОЛУЧИТЬ В ЗАКАЗЕ?</b>

📚 <b>Готовый проект</b>

Материал под твою тему с учётом задания и необходимых требований.

📊 <b>Презентация</b>

Наглядные слайды, которые можно использовать во время защиты.

🎤 <b>Материалы для выступления</b>

Понятный текст, который поможет тебе подготовиться к защите и рассказать о своей работе.

━━━━━━━━━━━━━━

💡 Наполнение заказа зависит от того, что именно тебе понадобится.

Если хочешь обсудить свой проект — нажми кнопку ниже.
"""

    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="📚 Оформить заявку",
        callback_data="order"
    )

    keyboard.button(
        text="🏠 Главное меню",
        callback_data="back"
    )

    keyboard.adjust(1)

    await callback.message.edit_text(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ПОЧЕМУ ВЫБИРАЮТ НАС
# =========================================================

@dp.callback_query(F.data == "why")
async def why(callback: CallbackQuery):

    save_user(callback.from_user)

    text = """
⭐ <b>ПОЧЕМУ SERGEY PROJECT?</b>

⏰ <b>Заранее договариваемся о сроках</b>

Сразу обсуждаем, к какой дате тебе понадобится готовая работа.

🎯 <b>Каждая заявка рассматривается отдельно</b>

Учитываем твою тему, предмет, класс и требования к заданию.

🧩 <b>Работа под конкретную задачу</b>

Не используем один и тот же вариант для всех — ориентируемся на твоё задание.

💬 <b>Можно связаться и задать вопрос</b>

Если нужно что-то уточнить или изменить, всегда можно написать.

🔎 <b>Внимание к требованиям</b>

Учитываем структуру, объём, оформление и другие условия задания.

🤝 <b>Простое общение</b>

Здесь не нужно писать официальным языком — общаемся нормально и на «ты».

━━━━━━━━━━━━━━

📌 Хочешь обсудить свой проект?

Оставь заявку — сначала разберёмся, что именно тебе нужно.
"""

    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="📚 Оформить заявку",
        callback_data="order"
    )

    keyboard.button(
        text="🏠 Главное меню",
        callback_data="back"
    )

    keyboard.adjust(1)

    await callback.message.edit_text(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# СВЯЗАТЬСЯ
# =========================================================

@dp.callback_query(F.data == "contact")
async def contact(
    callback: CallbackQuery,
    state: FSMContext
):

    save_user(callback.from_user)

    await state.clear()

    await state.set_state(
        ContactState.waiting_for_message
    )

    text = """
📞 <b>СВЯЗАТЬСЯ С SERGEY PROJECT</b>

Есть вопрос или хочешь что-то уточнить?

Просто напиши сообщение сюда 👇

💬 Можешь рассказать о своей ситуации своими словами — никаких шаблонов не нужно.

После отправки сообщение будет передано мне.
"""

    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="🏠 Назад в главное меню",
        callback_data="back"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# СООБЩЕНИЕ ЧЕРЕЗ "СВЯЗАТЬСЯ"
# =========================================================

@dp.message(ContactState.waiting_for_message)
async def receive_contact_message(
    message: Message,
    state: FSMContext
):

    save_user(message.from_user)

    if not message.text:

        await message.answer(
            "🙂 Напиши сообщение обычным текстом.",
            reply_markup=order_back_button()
        )

        return

    user = message.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "не указан"
    )

    safe_name = html.escape(user.full_name)
    safe_username = html.escape(username)
    safe_message = html.escape(message.text)

    admin_text = f"""
💬 <b>НОВОЕ СООБЩЕНИЕ</b>

👤 От: {safe_name}
🔗 Username: {safe_username}
🆔 Telegram ID: <code>{user.id}</code>

━━━━━━━━━━━━━━

💬 <b>Сообщение:</b>

{safe_message}
"""

    await bot.send_message(
        ADMIN_ID,
        admin_text,
        parse_mode="HTML",
        reply_markup=admin_reply_button(user.id)
    )

    await state.clear()

    await message.answer(
        """
✅ <b>СООБЩЕНИЕ ОТПРАВЛЕНО!</b>

Я получил твоё сообщение и скоро отвечу тебе.

🤝 Спасибо, что написал!
""",
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )


# =========================================================
# ОТВЕТ ПОЛЬЗОВАТЕЛЮ
# =========================================================

@dp.callback_query(F.data.startswith("reply_"))
async def reply_to_user(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "У тебя нет доступа.",
            show_alert=True
        )
        return

    try:
        user_id = int(
            callback.data.split("_")[1]
        )

    except (ValueError, IndexError):

        await callback.answer(
            "Ошибка пользователя.",
            show_alert=True
        )

        return

    await state.clear()

    await state.update_data(
        reply_user_id=user_id
    )

    await state.set_state(
        AdminReplyState.waiting_for_reply
    )

    await callback.message.answer(
        """
💬 <b>ОТВЕТ ПОЛЬЗОВАТЕЛЮ</b>

Напиши сообщение, которое хочешь отправить.

Оно будет отправлено пользователю от имени бота.

❌ Чтобы отменить — напиши <b>отмена</b>.
""",
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ОТПРАВКА ОТВЕТА
# =========================================================

@dp.message(AdminReplyState.waiting_for_reply)
async def send_admin_reply(
    message: Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    if not message.text:

        await message.answer(
            "🙂 Отправь обычный текст."
        )

        return

    if message.text.lower() == "отмена":

        await state.clear()

        await message.answer(
            "❌ Ответ отменён.",
            reply_markup=admin_menu()
        )

        return

    data = await state.get_data()

    user_id = data.get(
        "reply_user_id"
    )

    if not user_id:

        await state.clear()

        await message.answer(
            "❌ Не удалось определить пользователя.",
            reply_markup=admin_menu()
        )

        return

    try:

        safe_message = html.escape(
            message.text
        )

        await bot.send_message(
            user_id,
            f"""
💬 <b>Сообщение от SERGEY PROJECT</b>

{safe_message}

━━━━━━━━━━━━━━

Если хочешь что-то уточнить, можешь написать нам через раздел «📞 Связаться».
""",
            parse_mode="HTML"
        )

        await message.answer(
            "✅ Сообщение отправлено пользователю.",
            reply_markup=admin_menu()
        )

    except Exception:

        await message.answer(
            "❌ Не удалось отправить сообщение.\n\n"
            "Возможно, пользователь заблокировал бота.",
            reply_markup=admin_menu()
        )

    await state.clear()


# =========================================================
# АДМИН-ПАНЕЛЬ НАЗАД
# =========================================================

@dp.callback_query(F.data == "admin_back")
async def admin_back(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )

        return

    await state.clear()

    await callback.message.edit_text(
        """
🔐 <b>АДМИН-ПАНЕЛЬ</b>

👇 Выбери нужный раздел:
""",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ЗАКРЫТЬ АДМИН-ПАНЕЛЬ
# =========================================================

@dp.callback_query(F.data == "admin_close")
async def admin_close(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )

        return

    await callback.message.delete()

    await callback.answer()


# =========================================================
# ВОЗВРАТ В ГЛАВНОЕ МЕНЮ
# =========================================================

@dp.callback_query(F.data == "back")
async def back(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    save_user(callback.from_user)

    text = """
🎓 <b>SERGEY PROJECT</b>

Снова привет! 👋

Здесь ты можешь оформить заявку на индивидуальный учебный проект или посмотреть дополнительную информацию.

🤝 Всё просто: выбирай нужный раздел и пиши, если появились вопросы.

👇 Что тебя интересует?
"""

    await callback.message.edit_text(
        text,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# СЛУЧАЙНЫЕ СООБЩЕНИЯ
# =========================================================

@dp.message()
async def random_message(message: Message):

    save_user(message.from_user)

    await message.answer(
        """
🙂 Не совсем понял тебя.

Если хочешь оформить проект — нажми:

📚 <b>«Оформить заявку»</b>

А если у тебя есть вопрос — выбери:

📞 <b>«Связаться»</b>
""",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# =========================================================
# ЗАПУСК
# =========================================================

async def main():

    init_db()

    print("🤖 SERGEY PROJECT запущен!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
