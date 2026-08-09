import asyncio
import os
import html

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# =========================================================
# СОСТОЯНИЯ
# =========================================================

class OrderState(StatesGroup):
    waiting_for_order = State()
    confirmation = State()


class ContactState(StatesGroup):
    waiting_for_message = State()


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
# КНОПКА НАЗАД В ГЛАВНОЕ МЕНЮ
# =========================================================

def back_to_menu():
    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="🏠 Вернуться в главное меню",
        callback_data="back"
    )

    return keyboard.as_markup()


# =========================================================
# КНОПКА НАЗАД ПРИ ЗАПОЛНЕНИИ
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
# /START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):

    await state.clear()

    text = """
🎓 <b>SERGEY PROJECT</b>

Привет! 👋

Если тебе нужен индивидуальный учебный проект, презентация или материалы для защиты — ты по адресу.

🏫 Этот бот создан специально для учеников <b>МБОУ-СОШ №19 г. Армавира</b>.

Здесь ты можешь:

📚 Оформить заявку на проект
📦 Узнать, что входит в работу
⭐ Посмотреть, почему выбирают нас
💬 Ознакомиться с отзывами
📞 Задать свой вопрос

🤝 Общаемся здесь просто и по-дружески — без лишней официальности.

👇 Выбирай нужный раздел:
"""

    await message.answer(
        text,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# =========================================================
# ЧТО ВХОДИТ В РАБОТУ
# =========================================================

@dp.callback_query(F.data == "included")
async def included(callback: CallbackQuery):

    text = """
📦 <b>ЧТО МОЖНО ПОЛУЧИТЬ В ЗАКАЗЕ?</b>

📚 <b>Готовый проект</b>

Материал под твою тему с учетом задания и необходимых требований.

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

    text = """
⭐ <b>ПОЧЕМУ SERGEY PROJECT?</b>

⏰ <b>Заранее договариваемся о сроках</b>

Сразу обсуждаем, к какой дате тебе понадобится готовая работа.

🎯 <b>Каждая заявка рассматривается отдельно</b>

Учитываем твою тему, предмет, класс и требования к заданию.

🧩 <b>Работа под конкретную задачу</b>

Не просто выдаём случайную заготовку — учитываем то, что требуется именно тебе.

💬 <b>Можно связаться и задать вопрос</b>

Если нужно что-то уточнить или изменить, всегда можно написать.

🔎 <b>Внимание к требованиям</b>

Учитываем структуру, объем, оформление и другие условия задания.

🏫 <b>Для учеников МБОУ-СОШ №19</b>

Бот ориентирован именно на учеников нашей школы.

━━━━━━━━━━━━━━

📌 Хочешь обсудить свой проект?

Оставь заявку — сначала разберёмся, что тебе нужно.
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
# НАЧАЛО ОФОРМЛЕНИЯ ЗАЯВКИ
# =========================================================

@dp.callback_query(F.data == "order")
async def order(callback: CallbackQuery, state: FSMContext):

    await state.set_state(OrderState.waiting_for_order)

    text = """
📚 <b>ОФОРМЛЕНИЕ ЗАЯВКИ</b>

Давай быстро разберёмся, что тебе нужно.

Отправь одним сообщением:

🎓 <b>Класс / курс</b>
📖 <b>Предмет</b>
📝 <b>Тема проекта</b>
📅 <b>Когда нужна работа</b>
📦 <b>Что тебе требуется</b>

Например:

<b>10 класс
Физика
Электромагнитная индукция
Нужно к 25 августа
Проект + презентация + речь</b>

После этого я покажу тебе заявку перед отправкой.

⚠️ Пока ты не нажмёшь <b>«Отправить заявку»</b>, она никуда не уйдёт.
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
async def receive_order(message: Message, state: FSMContext):

    if not message.text:
        await message.answer(
            "🙂 Отправь, пожалуйста, информацию обычным текстовым сообщением.",
            reply_markup=order_back_button()
        )
        return

    await state.update_data(order_text=message.text)

    user = message.from_user

    username = f"@{user.username}" if user.username else "не указан"

    safe_name = html.escape(user.full_name)
    safe_username = html.escape(username)
    safe_order = html.escape(message.text)

    preview = f"""
📋 <b>ПРОВЕРЬ ЗАЯВКУ</b>

👤 <b>Имя:</b> {safe_name}
🔗 <b>Username:</b> {safe_username}

━━━━━━━━━━━━━━

📄 <b>Данные проекта:</b>

{safe_order}

━━━━━━━━━━━━━━

Всё верно?

Если всё правильно — нажми <b>«Отправить заявку»</b>.

⚠️ До этого момента заявка <b>не отправлена</b>.
"""

    await state.set_state(OrderState.confirmation)

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
async def send_order(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    order_text = data.get(
        "order_text",
        "Информация не указана"
    )

    user = callback.from_user

    username = f"@{user.username}" if user.username else "не указан"

    safe_name = html.escape(user.full_name)
    safe_username = html.escape(username)
    safe_order = html.escape(order_text)

    admin_text = f"""
📥 <b>НОВАЯ ЗАЯВКА</b>

👤 <b>Клиент:</b> {safe_name}
🔗 <b>Username:</b> {safe_username}
🆔 <b>Telegram ID:</b> {user.id}

━━━━━━━━━━━━━━

📄 <b>Заявка:</b>

{safe_order}
"""

    await bot.send_message(
        ADMIN_ID,
        admin_text,
        parse_mode="HTML"
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

    await callback.answer("Заявка отправлена! ✅")


# =========================================================
# ЗАПОЛНИТЬ ЗАНОВО
# =========================================================

@dp.callback_query(
    OrderState.confirmation,
    F.data == "edit_order"
)
async def edit_order(callback: CallbackQuery, state: FSMContext):

    await state.set_state(OrderState.waiting_for_order)

    text = """
✏️ <b>ЗАПОЛНИМ ЗАНОВО</b>

Отправь одним сообщением:

🎓 <b>Класс / курс</b>
📖 <b>Предмет</b>
📝 <b>Тема проекта</b>
📅 <b>Когда нужна работа</b>
📦 <b>Что тебе нужно</b>

Я снова покажу тебе заявку перед отправкой.
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
async def cancel_order(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    text = """
❌ <b>ЗАЯВКА ОТМЕНЕНА</b>

Ничего страшного 🙂

Если захочешь оформить её позже, просто вернись в главное меню.
"""

    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )

    await callback.answer("Заявка отменена")


# =========================================================
# СВЯЗАТЬСЯ
# =========================================================

@dp.callback_query(F.data == "contact")
async def contact(callback: CallbackQuery, state: FSMContext):

    await state.clear()
    await state.set_state(ContactState.waiting_for_message)

    text = """
📞 <b>СВЯЗАТЬСЯ С SERGEY PROJECT</b>

Есть вопрос или хочешь что-то уточнить?

Просто напиши сообщение сюда 👇

💬 Можешь рассказать о своей ситуации своими словами — без каких-либо шаблонов.

После отправки твоё сообщение будет передано мне.
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
# ПОЛУЧЕНИЕ СООБЩЕНИЯ ЧЕРЕЗ "СВЯЗАТЬСЯ"
# =========================================================

@dp.message(ContactState.waiting_for_message)
async def receive_contact_message(
    message: Message,
    state: FSMContext
):

    if not message.text:
        await message.answer(
            "🙂 Напиши, пожалуйста, сообщение обычным текстом.",
            reply_markup=order_back_button()
        )
        return

    user = message.from_user

    username = f"@{user.username}" if user.username else "не указан"

    safe_name = html.escape(user.full_name)
    safe_username = html.escape(username)
    safe_message = html.escape(message.text)

    admin_text = f"""
💬 <b>НОВОЕ СООБЩЕНИЕ</b>

👤 <b>От:</b> {safe_name}
🔗 <b>Username:</b> {safe_username}
🆔 <b>Telegram ID:</b> {user.id}

━━━━━━━━━━━━━━

💬 <b>Сообщение:</b>

{safe_message}
"""

    await bot.send_message(
        ADMIN_ID,
        admin_text,
        parse_mode="HTML"
    )

    await state.clear()

    text = """
✅ <b>СООБЩЕНИЕ ОТПРАВЛЕНО!</b>

Я получил твоё сообщение и скоро отвечу тебе.

🤝 Спасибо, что написал!
"""

    await message.answer(
        text,
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )


# =========================================================
# ВОЗВРАТ В ГЛАВНОЕ МЕНЮ
# =========================================================

@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    text = """
🎓 <b>SERGEY PROJECT</b>

Снова привет! 👋

Здесь ты можешь оформить заявку на индивидуальный учебный проект или посмотреть дополнительную информацию.

🏫 Бот создан для учеников <b>МБОУ-СОШ №19 г. Армавира</b>.

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

    text = """
🙂 <b>Не совсем понял тебя.</b>

Если хочешь оформить проект, нажми:

📚 <b>«Оформить заявку»</b>

А если у тебя просто вопрос — выбери раздел «Связаться».
"""

    await message.answer(
        text,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# =========================================================
# ЗАПУСК
# =========================================================

async def main():

    print("🤖 SERGEY PROJECT запущен!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
