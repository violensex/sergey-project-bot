import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv


# ==============================
# НАСТРОЙКИ
# ==============================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ==============================
# ГЛАВНОЕ МЕНЮ
# ==============================

def main_menu():
    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="📚 Оформить заказ",
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


# ==============================
# /START
# ==============================

@dp.message(CommandStart())
async def start(message: Message):

    text = """
🎓 <b>SERGEY PROJECT</b>

<b>Индивидуальные учебные проекты без лишней суеты.</b>

Если впереди защита, а времени на самостоятельную подготовку совсем немного — здесь можно оформить заказ на подготовку материалов для проекта.

📚 Работа подбирается под конкретную тему и требования.

🎤 Помимо самого проекта можно подготовить материалы для выступления.

📊 Также доступна презентация для защиты.

👇 Выберите интересующий раздел:
"""

    await message.answer(
        text,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# ==============================
# ЧТО ВХОДИТ В РАБОТУ
# ==============================

@dp.callback_query(F.data == "included")
async def included(callback: CallbackQuery):

    text = """
📦 <b>ЧТО МОЖНО ПОЛУЧИТЬ В ЗАКАЗЕ?</b>

📚 <b>Проект</b>

Основной материал по выбранной теме, подготовленный с учетом поставленной задачи.

📊 <b>Презентация</b>

Отдельные слайды для наглядного представления проекта во время выступления.

🎤 <b>Материалы для защиты</b>

Краткий и понятный текст, который поможет ориентироваться во время презентации.

━━━━━━━━━━━━━━

💡 Комплектация заказа зависит от того,
что именно требуется для вашей работы.

Чтобы узнать стоимость и обсудить детали,
нажмите кнопку ниже.
"""

    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="📚 Оформить заказ",
        callback_data="order"
    )

    keyboard.button(
        text="◀️ Главное меню",
        callback_data="back"
    )

    keyboard.adjust(1)

    await callback.message.edit_text(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

    await callback.answer()


# ==============================
# ПОЧЕМУ ВЫБИРАЮТ НАС
# ==============================

@dp.callback_query(F.data == "why")
async def why(callback: CallbackQuery):

    text = """
⭐ <b>ПОЧЕМУ SERGEY PROJECT?</b>

⏰ <b>Сроки заранее согласовываются</b>

Перед началом работы обсуждаем дедлайн, чтобы результат был готов к нужной дате.

🎯 <b>Каждый заказ рассматривается отдельно</b>

Мы учитываем тему, требования преподавателя и особенности конкретной работы.

🧩 <b>Без универсальных заготовок</b>

Материал формируется непосредственно под выбранную тему и задачу.

💬 <b>Связь на протяжении всего заказа</b>

Можно задать вопрос, уточнить детали или сообщить о необходимых изменениях.

🔎 <b>Внимание к требованиям</b>

При подготовке учитываются объем, структура, оформление и другие условия задания.

━━━━━━━━━━━━━━

📌 <b>Нужен проект?</b>

Оставьте заявку — сначала обсудим задачу,
а затем согласуем дальнейшие действия.
"""

    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="📚 Оформить заказ",
        callback_data="order"
    )

    keyboard.button(
        text="◀️ Главное меню",
        callback_data="back"
    )

    keyboard.adjust(1)

    await callback.message.edit_text(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

    await callback.answer()


# ==============================
# ОФОРМЛЕНИЕ ЗАКАЗА
# ==============================

@dp.callback_query(F.data == "order")
async def order(callback: CallbackQuery):

    text = """
📚 <b>НОВАЯ ЗАЯВКА</b>

Чтобы я мог быстро разобраться с задачей,
отправьте одним сообщением:

🎓 <b>Класс / курс:</b>
📖 <b>Предмет:</b>
📝 <b>Тема:</b>
📅 <b>Когда нужно:</b>
📦 <b>Что требуется:</b>

<b>Пример:</b>

<code>
Класс: 10
Предмет: история
Тема: Реформы Петра I
Срок: 28 августа
Нужно: проект + презентация
</code>

После получения информации заявка будет
передана для дальнейшего обсуждения.
"""

    await callback.message.answer(
        text,
        parse_mode="HTML"
    )

    await callback.answer()


# ==============================
# СВЯЗЬ
# ==============================

@dp.callback_query(F.data == "contact")
async def contact(callback: CallbackQuery):

    text = """
📞 <b>СВЯЗАТЬСЯ С SERGEY PROJECT</b>

Есть вопрос перед оформлением заказа?

Напишите сообщение в этот чат и опишите,
что именно вас интересует.

Если речь идет о конкретном проекте,
лучше сразу указать предмет и тему —
так будет проще быстро сориентироваться.

💬 <b>Мы обязательно ответим.</b>
"""

    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="◀️ Главное меню",
        callback_data="back"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

    await callback.answer()


# ==============================
# НАЗАД
# ==============================

@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):

    text = """
🎓 <b>SERGEY PROJECT</b>

Здесь можно оформить заявку на подготовку
индивидуального учебного проекта.

📚 Проект
📊 Презентация
🎤 Материалы для защиты

Все детали согласовываются перед началом работы.

👇 Выберите нужный раздел:
"""

    await callback.message.edit_text(
        text,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

    await callback.answer()


# ==============================
# ПОЛУЧЕНИЕ СООБЩЕНИЙ
# ==============================

@dp.message()
async def receive_order(message: Message):

    user = message.from_user

    if user.username:
        username = f"@{user.username}"
    else:
        username = "не указан"

    admin_text = f"""
📥 <b>НОВАЯ ЗАЯВКА</b>

👤 <b>Клиент:</b> {user.full_name}
🔗 <b>Username:</b> {username}
🆔 <b>Telegram ID:</b> <code>{user.id}</code>

━━━━━━━━━━━━━━

📄 <b>Сообщение клиента:</b>

{message.text}
"""

    await bot.send_message(
        ADMIN_ID,
        admin_text,
        parse_mode="HTML"
    )

    await message.answer(
        """
✅ <b>Сообщение получено!</b>

Информация отправлена администратору.

📩 С вами свяжутся для уточнения темы,
сроков и остальных деталей заказа.

🎓 <b>SERGEY PROJECT</b>
""",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ==============================
# ЗАПУСК БОТА
# ==============================

async def main():

    print("🤖 SERGEY PROJECT запущен!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
