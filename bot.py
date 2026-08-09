import asyncio
import os
import html
import json
from datetime import datetime

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
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

USERS_FILE = "users.json"
ORDERS_FILE = "orders.json"
PROMOCODES_FILE = "promocodes.json"

# ЦЕНЫ
PRICE_9 = 800
PRICE_10 = 1000


# =========================================================
# РАБОТА С JSON
# =========================================================

def load_json(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# ПОЛЬЗОВАТЕЛИ
# =========================================================

def load_users():
    return load_json(USERS_FILE, [])


def save_user(user_id):
    users = load_users()

    if user_id not in users:
        users.append(user_id)
        save_json(USERS_FILE, users)


# =========================================================
# ЗАЯВКИ
# =========================================================

def load_orders():
    return load_json(ORDERS_FILE, [])


def save_order(
    user,
    order_text,
    grade,
    price,
    promo_code=None,
    discount=0
):
    orders = load_orders()

    orders.append({
        "user_id": user.id,
        "name": user.full_name,
        "username": user.username or "",
        "text": order_text,
        "grade": grade,
        "price": price,
        "promo_code": promo_code or "",
        "discount": discount
    })

    save_json(ORDERS_FILE, orders)


# =========================================================
# ПРОМОКОДЫ
# =========================================================

def load_promocodes():
    return load_json(PROMOCODES_FILE, {})


def save_promocodes(promocodes):
    save_json(PROMOCODES_FILE, promocodes)


def create_promocode(
    code,
    discount,
    expires_at,
    max_uses
):
    promocodes = load_promocodes()

    promocodes[code.upper()] = {
        "discount": discount,
        "active": True,
        "expires_at": expires_at,
        "max_uses": max_uses,
        "uses": 0
    }

    save_promocodes(promocodes)


def get_promo_status(promo):
    """
    Возвращает:
    - "active" — промокод действителен
    - "expired" — срок истёк
    - "limit" — закончились использования
    - "disabled" — промокод выключен
    """

    if not promo.get("active", True):
        return "disabled"

    # Проверяем срок действия.
    # Старые промокоды без expires_at считаются бессрочными.
    expires_at = promo.get("expires_at")

    if expires_at:
        try:
            expiration = datetime.strptime(
                expires_at,
                "%d.%m.%Y %H:%M"
            )

            if datetime.now() > expiration:
                return "expired"

        except ValueError:
            # Если дата записана неправильно,
            # не блокируем старый промокод.
            pass

    # Проверяем количество использований.
    # Старые промокоды без max_uses считаются безлимитными.
    max_uses = promo.get("max_uses")

    if max_uses is not None:
        try:
            max_uses = int(max_uses)
            uses = int(promo.get("uses", 0))

            if uses >= max_uses:
                return "limit"

        except (ValueError, TypeError):
            pass

    return "active"


def check_promocode(code):
    promocodes = load_promocodes()

    code = code.upper().strip()

    if code not in promocodes:
        return None, "not_found"

    promo = promocodes[code]

    status = get_promo_status(promo)

    return promo, status


def use_promocode(code):
    """
    Засчитывает одно использование промокода.
    Возвращает True, если использование успешно засчитано.
    """

    promocodes = load_promocodes()

    code = code.upper().strip()

    if code not in promocodes:
        return False

    promo = promocodes[code]

    # Перед использованием ещё раз проверяем срок и лимит.
    status = get_promo_status(promo)

    if status != "active":
        return False

    current_uses = int(
        promo.get("uses", 0)
    )

    promo["uses"] = current_uses + 1

    save_promocodes(promocodes)

    return True


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


class PromoState(StatesGroup):
    waiting_for_code = State()


class AdminPromoState(StatesGroup):
    waiting_for_code = State()
    waiting_for_discount = State()
    waiting_for_expiration = State()
    waiting_for_max_uses = State()


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
        text="💰 Цены",
        callback_data="prices"
    )

    keyboard.button(
        text="📦 Что входит в работу",
        callback_data="included"
    )

    keyboard.button(
        text="💬 Отзывы",
        url="https://t.me/projectsergey1ak"
    )

    keyboard.button(
        text="🎟️ Промокод",
        callback_data="promo"
    )

    keyboard.button(
        text="📞 Связаться",
        callback_data="contact"
    )

    keyboard.adjust(1)

    return keyboard.as_markup()


# =========================================================
# НАЗАД
# =========================================================

def back_to_menu():
    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="🏠 Вернуться в главное меню",
        callback_data="back"
    )

    return keyboard.as_markup()


def order_back_button():
    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="🏠 Назад в главное меню",
        callback_data="back"
    )

    return keyboard.as_markup()


# =========================================================
# ВЫБОР КЛАССА
# =========================================================

def grade_keyboard():
    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="9️⃣ 9 класс — 800 ₽",
        callback_data="grade_9"
    )

    keyboard.button(
        text="🔟 10 класс — 1000 ₽",
        callback_data="grade_10"
    )

    keyboard.button(
        text="🏠 Назад",
        callback_data="back"
    )

    keyboard.adjust(1)

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
# ОТВЕТ АДМИНА
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
        text="📋 Последние заявки",
        callback_data="admin_orders"
    )

    keyboard.button(
        text="🎟️ Промокоды",
        callback_data="admin_promos"
    )

    keyboard.button(
        text="❌ Закрыть",
        callback_data="admin_close"
    )

    keyboard.adjust(2, 2, 1, 1)

    return keyboard.as_markup()


# =========================================================
# ПРОВЕРКА АДМИНА
# =========================================================

def is_admin(user_id):
    return user_id == ADMIN_ID


# =========================================================
# /START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):

    await state.clear()

    save_user(message.from_user.id)

    text = """
🎓 <b>SERGEY PROJECT</b>

Привет! 👋

Если тебе нужен индивидуальный учебный проект, презентация или материалы для защиты — ты по адресу.

🏫 Этот бот создан специально для учеников МБОУ-СОШ №19 г. Армавира.

Здесь ты можешь:

📚 Оформить заявку на проект
💰 Посмотреть цены
📦 Узнать, что входит в работу
💬 Ознакомиться с отзывами
🎟️ Активировать промокод
📞 Задать свой вопрос

👇 Выбирай нужный раздел:
"""

    await message.answer(
        text,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# =========================================================
# ЦЕНЫ
# =========================================================

@dp.callback_query(F.data == "prices")
async def prices(callback: CallbackQuery):

    save_user(callback.from_user.id)

    text = """
💰 <b>ЦЕНЫ</b>

9️⃣ <b>9 класс — 800 ₽</b>

🔟 <b>10 класс — 1000 ₽</b>

━━━━━━━━━━━━━━

Цена точная за проект под ключ в указанном диапазоне.

🎟️ При наличии промокода можно получить скидку.

⚠️ Чем ближе дата сдачи проекта, тем выше может становиться цена.
"""

    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ПРОМОКОД
# =========================================================

@dp.callback_query(F.data == "promo")
async def promo_start(
    callback: CallbackQuery,
    state: FSMContext
):

    save_user(callback.from_user.id)

    await state.set_state(
        PromoState.waiting_for_code
    )

    text = """
🎟️ <b>ПРОМОКОД</b>

Если у тебя есть промокод — отправь его сюда.

Я проверю его подлинность, срок действия и наличие свободных использований.

❌ Чтобы отменить, напиши <b>отмена</b>.
"""

    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )

    await callback.answer()


@dp.message(PromoState.waiting_for_code)
async def receive_promo(
    message: Message,
    state: FSMContext
):

    save_user(message.from_user.id)

    if not message.text:
        await message.answer(
            "🙂 Отправь промокод обычным текстом.",
            reply_markup=back_to_menu()
        )
        return

    if message.text.lower().strip() == "отмена":

        data = await state.get_data()

        promo_code = data.get("promo_code")
        discount = data.get("discount", 0)

        await state.clear()

        if promo_code:
            await state.update_data(
                promo_code=promo_code,
                discount=discount
            )

        await message.answer(
            "❌ Ввод промокода отменён.",
            reply_markup=main_menu()
        )

        return

    code = message.text.strip().upper()

    promo, status = check_promocode(code)

    # -----------------------------------------------------
    # ПРОМОКОД НЕ НАЙДЕН
    # -----------------------------------------------------

    if status == "not_found":

        await message.answer(
            """
❌ <b>Промокод не найден</b>

Такого промокода не существует.

Проверь код и попробуй ещё раз.
""",
            reply_markup=back_to_menu(),
            parse_mode="HTML"
        )

        return

    # -----------------------------------------------------
    # ПРОМОКОД ВЫКЛЮЧЕН
    # -----------------------------------------------------

    if status == "disabled":

        await message.answer(
            """
❌ <b>Промокод недействителен</b>

Этот промокод был отключён администратором.
""",
            reply_markup=back_to_menu(),
            parse_mode="HTML"
        )

        return

    # -----------------------------------------------------
    # ПРОМОКОД ИСТЁК
    # -----------------------------------------------------

    if status == "expired":

        expires_at = promo.get(
            "expires_at",
            ""
        )

        await message.answer(
            f"""
⏰ <b>ПРОМОКОД ИСТЁК</b>

К сожалению, срок действия промокода
<b>{html.escape(code)}</b> закончился.

📅 Действовал до: <b>{html.escape(expires_at)}</b>

Попробуй другой промокод.
""",
            reply_markup=back_to_menu(),
            parse_mode="HTML"
        )

        return

    # -----------------------------------------------------
    # ЗАКОНЧИЛИСЬ ИСПОЛЬЗОВАНИЯ
    # -----------------------------------------------------

    if status == "limit":

        max_uses = promo.get(
            "max_uses",
            0
        )

        await message.answer(
            f"""
❌ <b>ЛИМИТ ИСПОЛЬЗОВАНИЙ ИСЧЕРПАН</b>

Промокод <b>{html.escape(code)}</b>
больше нельзя использовать.

🔢 Максимум использований: <b>{max_uses}</b>

Попробуй другой промокод.
""",
            reply_markup=back_to_menu(),
            parse_mode="HTML"
        )

        return

    # -----------------------------------------------------
    # ПРОМОКОД ДЕЙСТВИТЕЛЕН
    # -----------------------------------------------------

    discount = promo.get(
        "discount",
        0
    )

    await state.update_data(
        promo_code=code,
        discount=discount
    )

    text = f"""
✅ <b>ПРОМОКОД ДЕЙСТВИТЕЛЕН!</b>

🎟️ Код: <b>{html.escape(code)}</b>
🔥 Скидка: <b>{discount}%</b>
"""

    # Показываем срок
    expires_at = promo.get("expires_at")

    if expires_at:
        text += (
            f"📅 Действует до: <b>{html.escape(expires_at)}</b>\n"
        )

    # Показываем количество использований
    max_uses = promo.get("max_uses")

    if max_uses is not None:

        uses = promo.get(
            "uses",
            0
        )

        remaining = int(max_uses) - int(uses)

        text += (
            f"🔢 Осталось использований: <b>{remaining}</b>\n"
        )

    text += """
    
━━━━━━━━━━━━━━

Промокод сохранён и автоматически применится при оформлении заявки.

👇 Можешь перейти к оформлению:
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

    await message.answer(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )


# =========================================================
# НАЧАЛО ЗАЯВКИ
# =========================================================

@dp.callback_query(F.data == "order")
async def order(
    callback: CallbackQuery,
    state: FSMContext
):

    save_user(callback.from_user.id)

    data = await state.get_data()

    promo_code = data.get("promo_code")
    discount = data.get("discount", 0)

    # Проверяем промокод ещё раз,
    # если он был сохранён ранее.
    if promo_code:

        promo, status = check_promocode(
            promo_code
        )

        if status != "active":

            await state.clear()

            if status == "expired":

                await callback.message.edit_text(
                    """
⏰ <b>ПРОМОКОД ИСТЁК</b>

Срок действия сохранённого промокода уже закончился.

Активируй другой промокод или продолжи без скидки.
""",
                    reply_markup=main_menu(),
                    parse_mode="HTML"
                )

                await callback.answer()

                return

            if status == "limit":

                await callback.message.edit_text(
                    """
❌ <b>ЛИМИТ ИСПОЛЬЗОВАНИЙ ИСЧЕРПАН</b>

К сожалению, этот промокод уже использовали максимальное количество раз.

Активируй другой промокод или продолжи без скидки.
""",
                    reply_markup=main_menu(),
                    parse_mode="HTML"
                )

                await callback.answer()

                return

            promo_code = None
            discount = 0

    await state.clear()

    await state.update_data(
        promo_code=promo_code,
        discount=discount,
        selecting_grade=True
    )

    await state.set_state(
        OrderState.waiting_for_order
    )

    if promo_code and discount:
        promo_info = f"""
🎟️ <b>Промокод применён</b>

Код: <b>{html.escape(promo_code)}</b>
🔥 Скидка: <b>{discount}%</b>

Сейчас выбери класс — после этого я покажу цену со скидкой.
"""
    else:
        promo_info = """
🎟️ Промокод не применён.

Если у тебя есть промокод, его можно активировать через главное меню.
"""

    text = f"""
📚 <b>ОФОРМЛЕНИЕ ЗАЯВКИ</b>

{promo_info}

━━━━━━━━━━━━━━

🎓 <b>Выбери свой класс:</b>
"""

    await callback.message.edit_text(
        text,
        reply_markup=grade_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# 9 КЛАСС
# =========================================================

@dp.callback_query(
    OrderState.waiting_for_order,
    F.data == "grade_9"
)
async def grade_9(
    callback: CallbackQuery,
    state: FSMContext
):

    await select_grade(
        callback,
        state,
        "9 класс",
        PRICE_9
    )


# =========================================================
# 10 КЛАСС
# =========================================================

@dp.callback_query(
    OrderState.waiting_for_order,
    F.data == "grade_10"
)
async def grade_10(
    callback: CallbackQuery,
    state: FSMContext
):

    await select_grade(
        callback,
        state,
        "10 класс",
        PRICE_10
    )


# =========================================================
# ОБРАБОТКА КЛАССА
# =========================================================

async def select_grade(
    callback: CallbackQuery,
    state: FSMContext,
    grade,
    base_price
):

    data = await state.get_data()

    promo_code = data.get("promo_code")
    discount = data.get("discount", 0)

    # Ещё одна проверка промокода.
    if promo_code:

        promo, status = check_promocode(
            promo_code
        )

        if status != "active":

            await state.update_data(
                promo_code=None,
                discount=0
            )

            promo_code = None
            discount = 0

            if status == "expired":

                await callback.answer(
                    "⏰ Промокод истёк. Скидка отменена.",
                    show_alert=True
                )

            elif status == "limit":

                await callback.answer(
                    "❌ Лимит использований промокода исчерпан.",
                    show_alert=True
                )

            else:

                await callback.answer(
                    "❌ Промокод больше недействителен.",
                    show_alert=True
                )

    try:
        discount = int(discount)
    except (ValueError, TypeError):
        discount = 0

    if discount < 0 or discount > 100:
        discount = 0

    final_price = base_price

    if discount:
        final_price = round(
            base_price * (100 - discount) / 100
        )

    await state.update_data(
        grade=grade,
        base_price=base_price,
        final_price=final_price,
        promo_code=promo_code,
        discount=discount,
        selecting_grade=False
    )

    if promo_code and discount:

        price_text = f"""
💰 Обычная цена: <s>{base_price} ₽</s>

🎟️ Промокод: <b>{html.escape(promo_code)}</b>

🔥 Скидка: <b>{discount}%</b>

🎉 <b>Цена со скидкой: {final_price} ₽</b>
"""

    else:

        price_text = f"""
💰 <b>Цена за проект под ключ: {final_price} ₽</b>
"""

    text = f"""
✅ <b>Выбран {grade}</b>

{price_text}

━━━━━━━━━━━━━━

Теперь отправь <b>одним сообщением всю информацию по проекту</b>.

Напиши тему, предмет, требования, срок сдачи и всё остальное, что нужно знать о работе.

После этого я покажу тебе заявку перед отправкой.
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

    save_user(message.from_user.id)

    data = await state.get_data()

    if data.get("selecting_grade"):

        await message.answer(
            "👇 Сначала выбери класс кнопкой выше.",
            reply_markup=grade_keyboard()
        )

        return

    if not message.text:

        await message.answer(
            "🙂 Отправь информацию обычным текстовым сообщением.",
            reply_markup=order_back_button()
        )

        return

    await state.update_data(
        order_text=message.text
    )

    data = await state.get_data()

    grade = data.get(
        "grade",
        "не указан"
    )

    final_price = data.get(
        "final_price",
        0
    )

    promo_code = data.get(
        "promo_code"
    )

    discount = data.get(
        "discount",
        0
    )

    safe_order = html.escape(
        message.text
    )

    if promo_code and discount:

        price_info = (
            f"🎟️ Промокод: <b>{html.escape(promo_code)}</b>\n"
            f"🔥 Скидка: <b>{discount}%</b>\n"
            f"💰 Цена со скидкой: <b>{final_price} ₽</b>"
        )

    else:

        price_info = (
            f"💰 Цена: <b>{final_price} ₽</b>"
        )

    preview = f"""
📋 <b>ЗАЯВКА</b>

🎓 Класс: <b>{html.escape(grade)}</b>

{price_info}

━━━━━━━━━━━━━━

📄 <b>Информация по проекту:</b>

{safe_order}

━━━━━━━━━━━━━━

Всё верно?

Если всё правильно — нажми «Отправить заявку».

До этого момента заявка никуда не отправлена.
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

    grade = data.get(
        "grade",
        "не указан"
    )

    final_price = data.get(
        "final_price",
        0
    )

    promo_code = data.get(
        "promo_code"
    )

    discount = data.get(
        "discount",
        0
    )

    # -----------------------------------------------------
    # ФИНАЛЬНАЯ ПРОВЕРКА ПРОМОКОДА
    # -----------------------------------------------------

    if promo_code and discount:

        promo, status = check_promocode(
            promo_code
        )

        if status == "expired":

            await state.clear()

            await callback.message.edit_text(
                """
⏰ <b>ПРОМОКОД ИСТЁК</b>

Пока ты оформлял заявку, срок действия промокода закончился.

Заявка <b>не отправлена</b>.

Можешь оформить её заново без промокода или использовать другой действующий промокод.
""",
                reply_markup=main_menu(),
                parse_mode="HTML"
            )

            await callback.answer(
                "Промокод истёк.",
                show_alert=True
            )

            return

        if status == "limit":

            await state.clear()

            await callback.message.edit_text(
                """
❌ <b>ЛИМИТ ИСПОЛЬЗОВАНИЙ ИСЧЕРПАН</b>

Пока ты оформлял заявку, свободные использования этого промокода закончились.

Заявка <b>не отправлена</b>.

Можешь оформить её заново без промокода или использовать другой промокод.
""",
                reply_markup=main_menu(),
                parse_mode="HTML"
            )

            await callback.answer(
                "Лимит промокода исчерпан.",
                show_alert=True
            )

            return

        if status != "active":

            await state.clear()

            await callback.message.edit_text(
                """
❌ <b>ПРОМОКОД НЕДЕЙСТВИТЕЛЕН</b>

Этот промокод больше нельзя использовать.

Заявка <b>не отправлена</b>.
""",
                reply_markup=main_menu(),
                parse_mode="HTML"
            )

            await callback.answer(
                "Промокод недействителен.",
                show_alert=True
            )

            return

        # Засчитываем использование только сейчас,
        # когда пользователь реально отправляет заявку.
        if not use_promocode(promo_code):

            await state.clear()

            await callback.message.edit_text(
                """
❌ <b>НЕ УДАЛОСЬ ПРИМЕНИТЬ ПРОМОКОД</b>

К сожалению, этот промокод только что стал недействительным или закончились его использования.

Заявка <b>не отправлена</b>.
""",
                reply_markup=main_menu(),
                parse_mode="HTML"
            )

            await callback.answer(
                "Промокод больше недействителен.",
                show_alert=True
            )

            return

    user = callback.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "не указан"
    )

    safe_name = html.escape(
        user.full_name
    )

    safe_username = html.escape(
        username
    )

    safe_order = html.escape(
        order_text
    )

    save_order(
        user,
        order_text,
        grade,
        final_price,
        promo_code,
        discount
    )

    if promo_code and discount:

        promo_info = (
            f"🎟️ Промокод: <b>{html.escape(promo_code)}</b>\n"
            f"🔥 Скидка: <b>{discount}%</b>\n"
            f"💰 Цена: <b>{final_price} ₽</b>"
        )

    else:

        promo_info = (
            f"💰 Цена: <b>{final_price} ₽</b>"
        )

    admin_text = f"""
📥 <b>НОВАЯ ЗАЯВКА</b>

👤 Клиент: {safe_name}
🔗 Username: {safe_username}
🆔 Telegram ID: {user.id}

━━━━━━━━━━━━━━

🎓 Класс: <b>{html.escape(grade)}</b>

{promo_info}

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

Скоро с тобой свяжутся, чтобы обсудить детали проекта, сроки и всё необходимое.

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

    data = await state.get_data()

    grade = data.get(
        "grade",
        "не указан"
    )

    promo_code = data.get(
        "promo_code"
    )

    discount = data.get(
        "discount",
        0
    )

    await state.set_state(
        OrderState.waiting_for_order
    )

    await state.update_data(
        grade=grade,
        promo_code=promo_code,
        discount=discount,
        selecting_grade=False
    )

    text = f"""
✏️ <b>ЗАПОЛНИМ ЗАНОВО</b>

🎓 Класс: <b>{html.escape(grade)}</b>
"""

    if promo_code and discount:

        text += f"""
🎟️ Промокод: <b>{html.escape(promo_code)}</b>
🔥 Скидка: <b>{discount}%</b>
"""

    text += """
━━━━━━━━━━━━━━

Отправь <b>одним сообщением всю информацию по проекту</b>.

Можешь указать тему, предмет, требования, срок сдачи и всё остальное, что необходимо знать.
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
# ЧТО ВХОДИТ
# =========================================================

@dp.callback_query(F.data == "included")
async def included(callback: CallbackQuery):

    save_user(callback.from_user.id)

    text = """
📦 <b>ЧТО МОЖНО ПОЛУЧИТЬ В ЗАКАЗЕ?</b>

📚 <b>Готовый проект</b>

Материал под твою тему с учетом задания и необходимых требований.

📊 <b>Презентация</b>

Наглядные слайды, которые можно использовать во время защиты.

🎤 <b>Материалы для выступления</b>

Понятный текст, который поможет подготовиться к защите и рассказать о своей работе.

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
# СВЯЗАТЬСЯ
# =========================================================

@dp.callback_query(F.data == "contact")
async def contact(
    callback: CallbackQuery,
    state: FSMContext
):

    save_user(callback.from_user.id)

    await state.clear()

    await state.set_state(
        ContactState.waiting_for_message
    )

    text = """
📞 <b>СВЯЗАТЬСЯ С SERGEY PROJECT</b>

Есть вопрос или хочешь что-то уточнить?

Просто напиши сообщение сюда 👇

💬 Можешь рассказать о своей ситуации своими словами — без шаблонов.

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
# СООБЩЕНИЕ АДМИНУ
# =========================================================

@dp.message(ContactState.waiting_for_message)
async def receive_contact_message(
    message: Message,
    state: FSMContext
):

    save_user(message.from_user.id)

    if not message.text:

        await message.answer(
            "🙂 Напиши, пожалуйста, сообщение обычным текстом.",
            reply_markup=back_to_menu()
        )

        return

    user = message.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "не указан"
    )

    safe_name = html.escape(
        user.full_name
    )

    safe_username = html.escape(
        username
    )

    safe_message = html.escape(
        message.text
    )

    admin_text = f"""
💬 <b>НОВОЕ СООБЩЕНИЕ</b>

👤 От: {safe_name}
🔗 Username: {safe_username}
🆔 Telegram ID: {user.id}

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

    if message.text.lower().strip() == "отмена":

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
            "❌ Не удалось определить пользователя."
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
# /ADMIN
# =========================================================

@dp.message(Command("admin"))
async def admin_command(
    message: Message,
    state: FSMContext
):

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

👇 Выбери нужный раздел:
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

    users = load_users()
    orders = load_orders()
    promos = load_promocodes()

    average = (
        round(len(orders) / len(users), 2)
        if users
        else 0
    )

    text = f"""
📊 <b>СТАТИСТИКА</b>

👥 Пользователей: <b>{len(users)}</b>

📚 Всего заявок: <b>{len(orders)}</b>

🎟️ Промокодов: <b>{len(promos)}</b>

💬 Среднее количество заявок на пользователя:
<b>{average}</b>
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

    users = load_users()

    text = f"""
👥 <b>ПОЛЬЗОВАТЕЛИ</b>

Сейчас бот знает о:

<b>{len(users)}</b> пользователях.

Все пользователи автоматически добавляются в список после нажатия /start.

Этот список используется для рассылки.
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
# ПОСЛЕДНИЕ ЗАЯВКИ
# =========================================================

@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )

        return

    orders = load_orders()

    if not orders:

        text = """
📋 <b>ПОСЛЕДНИЕ ЗАЯВКИ</b>

Пока заявок нет.
"""

    else:

        recent_orders = orders[-5:]
        recent_orders.reverse()

        text = "📋 <b>ПОСЛЕДНИЕ ЗАЯВКИ</b>\n\n"

        for number, order_item in enumerate(
            recent_orders,
            1
        ):

            username = (
                f"@{order_item['username']}"
                if order_item.get("username")
                else "не указан"
            )

            safe_name = html.escape(
                order_item.get("name", "Без имени")
            )

            safe_username = html.escape(
                username
            )

            safe_text = html.escape(
                order_item.get("text", "")
            )

            grade = html.escape(
                str(
                    order_item.get(
                        "grade",
                        "не указан"
                    )
                )
            )

            price = order_item.get(
                "price",
                0
            )

            promo_code = order_item.get(
                "promo_code",
                ""
            )

            discount = order_item.get(
                "discount",
                0
            )

            promo_info = ""

            if promo_code:

                promo_info = (
                    f"\n🎟️ {html.escape(promo_code)}"
                    f" — {discount}%"
                )

            text += f"""
<b>{number}. {safe_name}</b>

🔗 {safe_username}
🆔 {order_item.get('user_id', 'не указан')}
🎓 {grade}
💰 {price} ₽{promo_info}

{safe_text}

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
# ПРОМОКОДЫ — АДМИН
# =========================================================

@dp.callback_query(F.data == "admin_promos")
async def admin_promos(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )

        return

    promos = load_promocodes()

    if not promos:

        promo_text = "Промокодов пока нет."

    else:

        promo_text = ""

        for code, promo in promos.items():

            status = get_promo_status(promo)

            if status == "active":
                status_text = "🟢 активен"

            elif status == "expired":
                status_text = "⏰ истёк"

            elif status == "limit":
                status_text = "🔴 лимит исчерпан"

            elif status == "disabled":
                status_text = "🔴 выключен"

            else:
                status_text = "⚪ неизвестно"

            discount = promo.get(
                "discount",
                0
            )

            uses = promo.get(
                "uses",
                0
            )

            max_uses = promo.get(
                "max_uses"
            )

            expires_at = promo.get(
                "expires_at"
            )

            # Информация о лимите
            if max_uses is None:
                uses_text = f"{uses}/∞"

            else:
                uses_text = (
                    f"{uses}/{max_uses}"
                )

            # Информация о сроке
            if expires_at:
                expiration_text = (
                    f"\n📅 До: <b>{html.escape(expires_at)}</b>"
                )
            else:
                expiration_text = (
                    "\n📅 До: <b>бессрочно</b>"
                )

            promo_text += (
                f"🎟️ <b>{html.escape(code)}</b>\n"
                f"🔥 Скидка: <b>{discount}%</b>\n"
                f"🔢 Использований: <b>{uses_text}</b>"
                f"{expiration_text}\n"
                f"📌 Статус: <b>{status_text}</b>\n"
                f"━━━━━━━━━━━━━━\n"
            )

    text = f"""
🎟️ <b>ПРОМОКОДЫ</b>

{promo_text}

Здесь можно создавать новые промокоды.
"""

    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="➕ Создать промокод",
        callback_data="admin_create_promo"
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
# СОЗДАНИЕ ПРОМОКОДА
# =========================================================

@dp.callback_query(F.data == "admin_create_promo")
async def admin_create_promo(
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
        AdminPromoState.waiting_for_code
    )

    await callback.message.edit_text(
        """
➕ <b>СОЗДАНИЕ ПРОМОКОДА</b>

<b>Шаг 1 из 4</b>

Отправь код промокода.

Например:

<b>SCHOOL10</b>

❌ Для отмены напиши: <b>отмена</b>
""",
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# КОД ПРОМОКОДА
# =========================================================

@dp.message(AdminPromoState.waiting_for_code)
async def receive_admin_promo_code(
    message: Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    if not message.text:

        await message.answer(
            "🙂 Отправь промокод обычным текстом."
        )

        return

    if message.text.lower().strip() == "отмена":

        await state.clear()

        await message.answer(
            "❌ Создание промокода отменено.",
            reply_markup=admin_menu()
        )

        return

    code = message.text.strip().upper()

    if " " in code:

        await message.answer(
            "❌ Промокод не должен содержать пробелов."
        )

        return

    if len(code) > 30:

        await message.answer(
            "❌ Промокод слишком длинный."
        )

        return

    promos = load_promocodes()

    if code in promos:

        await message.answer(
            f"""
❌ <b>Такой промокод уже существует</b>

Промокод <b>{html.escape(code)}</b> уже есть в системе.

Введи другой код.
""",
            parse_mode="HTML"
        )

        return

    await state.update_data(
        new_promo_code=code
    )

    await state.set_state(
        AdminPromoState.waiting_for_discount
    )

    await message.answer(
        f"""
🎟️ Код: <b>{html.escape(code)}</b>

<b>Шаг 2 из 4</b>

Теперь отправь размер скидки в процентах.

Например:

<b>10</b>

Это будет скидка 10%.

❌ Для отмены напиши: <b>отмена</b>
""",
        parse_mode="HTML"
    )


# =========================================================
# СКИДКА
# =========================================================

@dp.message(AdminPromoState.waiting_for_discount)
async def receive_admin_promo_discount(
    message: Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    if not message.text:

        await message.answer(
            "🙂 Отправь число от 1 до 100."
        )

        return

    if message.text.lower().strip() == "отмена":

        await state.clear()

        await message.answer(
            "❌ Создание промокода отменено.",
            reply_markup=admin_menu()
        )

        return

    try:

        discount = int(
            message.text.strip()
        )

    except ValueError:

        await message.answer(
            "❌ Введи целое число от 1 до 100."
        )

        return

    if discount < 1 or discount > 100:

        await message.answer(
            "❌ Скидка должна быть от 1 до 100%."
        )

        return

    await state.update_data(
        new_promo_discount=discount
    )

    await state.set_state(
        AdminPromoState.waiting_for_expiration
    )

    await message.answer(
        """
📅 <b>Шаг 3 из 4</b>

Теперь укажи срок действия промокода.

Формат:

<b>ДД.ММ.ГГГГ ЧЧ:ММ</b>

Например:

<b>31.08.2026 23:59</b>

Промокод будет действовать до указанной даты и времени.

❌ Для отмены напиши: <b>отмена</b>
""",
        parse_mode="HTML"
    )


# =========================================================
# СРОК ДЕЙСТВИЯ
# =========================================================

@dp.message(AdminPromoState.waiting_for_expiration)
async def receive_admin_promo_expiration(
    message: Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    if not message.text:

        await message.answer(
            "🙂 Отправь дату обычным текстом."
        )

        return

    if message.text.lower().strip() == "отмена":

        await state.clear()

        await message.answer(
            "❌ Создание промокода отменено.",
            reply_markup=admin_menu()
        )

        return

    expiration_text = message.text.strip()

    try:

        expiration = datetime.strptime(
            expiration_text,
            "%d.%m.%Y %H:%M"
        )

    except ValueError:

        await message.answer(
            """
❌ <b>Неверный формат даты.</b>

Используй формат:

<b>ДД.ММ.ГГГГ ЧЧ:ММ</b>

Например:

<b>31.08.2026 23:59</b>
""",
            parse_mode="HTML"
        )

        return

    if expiration <= datetime.now():

        await message.answer(
            """
❌ Эта дата уже прошла.

Укажи дату и время в будущем.
""",
            parse_mode="HTML"
        )

        return

    await state.update_data(
        new_promo_expires_at=expiration_text
    )

    await state.set_state(
        AdminPromoState.waiting_for_max_uses
    )

    await message.answer(
        """
🔢 <b>Шаг 4 из 4</b>

Теперь укажи максимальное количество использований промокода.

Например:

<b>50</b>

Это значит, что промокод смогут использовать максимум 50 раз.

❌ Для отмены напиши: <b>отмена</b>
""",
        parse_mode="HTML"
    )


# =========================================================
# МАКСИМАЛЬНОЕ КОЛИЧЕСТВО ИСПОЛЬЗОВАНИЙ
# =========================================================

@dp.message(AdminPromoState.waiting_for_max_uses)
async def receive_admin_promo_max_uses(
    message: Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    if not message.text:

        await message.answer(
            "🙂 Отправь целое число больше 0."
        )

        return

    if message.text.lower().strip() == "отмена":

        await state.clear()

        await message.answer(
            "❌ Создание промокода отменено.",
            reply_markup=admin_menu()
        )

        return

    try:

        max_uses = int(
            message.text.strip()
        )

    except ValueError:

        await message.answer(
            "❌ Введи целое число больше 0."
        )

        return

    if max_uses < 1:

        await message.answer(
            "❌ Количество использований должно быть больше 0."
        )

        return

    data = await state.get_data()

    code = data.get(
        "new_promo_code"
    )

    discount = data.get(
        "new_promo_discount"
    )

    expires_at = data.get(
        "new_promo_expires_at"
    )

    if not code or discount is None or not expires_at:

        await state.clear()

        await message.answer(
            "❌ Ошибка: данные промокода потеряны.",
            reply_markup=admin_menu()
        )

        return

    create_promocode(
        code=code,
        discount=discount,
        expires_at=expires_at,
        max_uses=max_uses
    )

    await state.clear()

    await message.answer(
        f"""
✅ <b>ПРОМОКОД СОЗДАН!</b>

🎟️ Код: <b>{html.escape(code)}</b>

🔥 Скидка: <b>{discount}%</b>

📅 Действует до:
<b>{html.escape(expires_at)}</b>

🔢 Максимум использований:
<b>{max_uses}</b>

🔢 Уже использовано:
<b>0/{max_uses}</b>

🟢 Статус: <b>активен</b>
""",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )


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

После этого я покажу предпросмотр и попрошу подтвердить отправку.

❌ Чтобы отменить — напиши <b>отмена</b>.
""",
        parse_mode="HTML"
    )

    await callback.answer()


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

    if message.text.lower().strip() == "отмена":

        await state.clear()

        await message.answer(
            "❌ Рассылка отменена.",
            reply_markup=admin_menu()
        )

        return

    await state.update_data(
        broadcast_text=message.text
    )

    safe_text = html.escape(
        message.text
    )

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

👥 Получателей: <b>{len(load_users())}</b>

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

    users = load_users()

    await callback.message.edit_text(
        "📢 <b>Рассылка началась...</b>\n\n"
        "Пожалуйста, подожди.",
        parse_mode="HTML"
    )

    success = 0
    failed = 0

    safe_text = html.escape(
        broadcast_text
    )

    for user_id in users:

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
async def admin_close(
    callback: CallbackQuery
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )

        return

    await callback.message.delete()

    await callback.answer()


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

@dp.callback_query(F.data == "back")
async def back(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    save_user(callback.from_user.id)

    text = """
🎓 <b>SERGEY PROJECT</b>

Снова привет! 👋

Здесь ты можешь оформить заявку на индивидуальный учебный проект или посмотреть дополнительную информацию.

🏫 Бот создан специально для учеников МБОУ-СОШ №19 г. Армавира.

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
async def random_message(
    message: Message
):

    save_user(message.from_user.id)

    await message.answer(
        """
🙂 Не совсем понял тебя.

Если хочешь оформить проект, нажми:

📚 «Оформить заявку»

А если у тебя просто вопрос — выбери раздел «📞 Связаться».
""",
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
