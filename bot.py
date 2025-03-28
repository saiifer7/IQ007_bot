from PIL import Image
import logging
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import *
import asyncio
import os
from dotenv import load_dotenv
from database import get_user, set_user, find_user_by_username

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

ALLOWED_ADMINS = [229210929]
admin_states = {}

characters = {
    "knight": {"name": "Рыцарь Лис"},
    "fairy": {"name": "Фея Лиса"},
    "dwarf": {"name": "Гном Лис"},
    "elf": {"name": "Эльф Лиса"},
    "wizard": {"name": "Волшебник Лис"},
}

# Функция прокачки XP и уровня
def add_xp(user, amount):
    user["xp"] += amount
    while user["xp"] >= 100 and user["level"] < 5:
        user["xp"] -= 100
        user["level"] += 1
    return user

def get_main_menu(is_admin=False, user_data=None):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.add(KeyboardButton("🦸🏻 Мой герой"))

    # Кнопка прокачки школы
    if user_data:
        level = user_data.get("school_level", 0)
        if level < 3:
            cost_map = {0: 50, 1: 150, 2: 300}
            cost = cost_map[level]
            keyboard.add(KeyboardButton(f"🏫 Прокачать школу ({cost} коинов)"))
        else:
            keyboard.add(KeyboardButton("🏫 Школа прокачана на максимум!"))
        
        # Кнопка магазина
        keyboard.add(KeyboardButton("🛒 Магазин улучшений"))

        # Кнопка награды дня
        today = str(datetime.now().date())
        if user_data.get("last_reward_date") == today:
            keyboard.add(KeyboardButton("🎁 Награда уже получена сегодня"))
        else:
            keyboard.add(KeyboardButton("🎁 Получить награду дня"))
    else:
        keyboard.add(KeyboardButton("🏫 Прокачать школу"))
        keyboard.add(KeyboardButton("🎁 Получить награду дня"))

    keyboard.add(KeyboardButton("🆔 Узнать свой ID"))
    if is_admin:
        keyboard.add(KeyboardButton("👩‍🏫 Админ-панель"))

    return keyboard

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username

    user = get_user(user_id)
    if user:
        await message.answer("Ты уже выбрал персонажа. Поменять его нельзя, но ты можешь продолжать развивать своего героя!", reply_markup=get_main_menu(user_id in ALLOWED_ADMINS, user))
        return

   
        await message.answer(
    """Привет!

Перед тобой 5 героев. Ты можешь посмотреть каждого и выбрать того, кто тебе по душе.
После активации героя ты уже не сможешь его поменять, так что выбирай с умом!

*Нажми «АКТИВИРОВАТЬ ГЕРОЯ ✅» под понравившимся.*""",
    parse_mode="Markdown"
    )

    for key, value in characters.items():
        img_path = f"characters/{key}_lvl1.png"
        try:
            img = InputFile(img_path)
        except:
            continue

        descriptions = {
            "knight": "🛡️ *Смелый защитник знаний.*\nОн всегда готов сражаться с ленью и скукой.",
            "fairy": "🧚 *Волшебница вдохновения.*\nПревращает занятия в сказочные приключения.",
            "dwarf": "⛏️ *Настойчивый мастер.*\nШаг за шагом строит фундамент знаний.",
            "elf":   "🏹 *Быстрая и мудрая.*\nПомогает точно попадать в цель и быстро мыслить.",
            "wizard":"🪄 *Хранитель великих тайн.*\nОткрывает секреты и прокачивает интеллект."
        }

        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("АКТИВИРОВАТЬ ГЕРОЯ ✅", callback_data=f"activate_{key}")
        )

        await message.answer_photo(
            photo=img,
            caption=descriptions[key],
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

        await asyncio.sleep(7)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("activate_"))
async def activate_character(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username
    user = get_user(user_id)

    if user:
        await callback_query.answer("Ты уже выбрал героя.")
        return

    char_key = callback_query.data.split("_")[1]

    user_data = {
        "character": char_key,
        "level": 1,
        "xp": 0,
        "coins": 0,
        "school_level": 0,
        "last_reward_date": None,
        "username": username
    }

    set_user(user_id, user_data)

    await bot.answer_callback_query(callback_query.id)

    await bot.send_message(user_id, f"Герой *{characters[char_key]['name']}* успешно активирован!\n\nВперёд к приключениям!", parse_mode="Markdown")

    tutorial = [
        "Ура! Теперь ты — герой школы IQ007!\nТы выбрал своего персонажа, а это значит — пора в путь!",
        "Каждое занятие — это шаг к победе!\nТы будешь получать ⭐ XP и 💰 коины.",
        "XP помогает прокачивать героя — ты растёшь в уровнях и становишься сильнее!",
        "А коины можно тратить на прокачку школы — она поможет получать ещё больше наград!",
        "А теперь — заглянем к твоему герою!"
    ]

    for msg in tutorial:
        await asyncio.sleep(2.5)
        await bot.send_message(user_id, msg)

    await handle_status(callback_query.message)

from PIL import Image

@dp.message_handler(lambda message: message.text == "🦸🏻 Мой герой")
async def handle_status(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("Сначала выбери персонажа с помощью /start.")
        return

    char_key = user["character"]
    level = min(user["level"], 5)
    base_path = f"characters/{char_key}_lvl{level}.png"

    try:
        base = Image.open(base_path).convert("RGBA")

        # Накладываем все предметы
        for item_id in user.get("items", []):
            try:
                overlay = Image.open(shop_items[item_id]["image"]).convert("RGBA")
                base.alpha_composite(overlay)
            except:
                continue

        final_path = f"temp/{user_id}_final.png"
        os.makedirs("temp", exist_ok=True)
        base.save(final_path)
        img = InputFile(final_path)
    except:
        await message.answer("Картинка персонажа не найдена.")
        return

    # Эмодзи для персонажей
    char_emojis = {
        "knight": "🛡️",
        "fairy": "🧚",
        "dwarf": "⛏️",
        "elf": "🏹",
        "wizard": "🪄"
    }
    emoji = char_emojis.get(char_key, "🎮")

    xp_bar = "[" + "█" * (user["xp"] % 100 // 10) + "░" * (10 - (user["xp"] % 100 // 10)) + "]"
    school_level = user["school_level"]
    school_stars = "⭐️" * school_level + "★" * (3 - school_level)
    coins_per_lesson = 10 + user["level"] * 5 + user["school_level"] * 5

    text = (
        f"{emoji} *{characters[char_key]['name']}*\n"
        f"🆙 Уровень: *{user['level']}*\n"
        f"💫 Опыт: *{user['xp']}* {xp_bar}\n"
        f"💰 Коины: *{user['coins']}*\n"
        f"🏫 Уровень школы: {school_stars}\n\n"
        f"➕ За 1 урок: *+10 XP*, *+{coins_per_lesson} коинов*"
    )

    await message.answer_photo(photo=img, caption=text, parse_mode="Markdown", reply_markup=get_main_menu(user_id in ALLOWED_ADMINS, user))

@dp.message_handler(lambda msg: msg.text.startswith("🏫 Прокачать школу"))
async def upgrade_school(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("Сначала выбери персонажа.")
        return

    level = user["school_level"]
    cost_map = {0: 50, 1: 150, 2: 300}

    if level >= 3:
        await message.answer("Твоя школа уже прокачана на максимум! ⭐️⭐️⭐️")
        return

    cost = cost_map[level]
    if user["coins"] < cost:
        await message.answer(f"Не хватает коинов. Нужно {cost}, у тебя {user['coins']}.")
        return

    user["coins"] -= cost
    user["school_level"] += 1
    set_user(user_id, user)
    await message.answer(f"Поздравляем! Школа улучшена до уровня {user['school_level']}!", reply_markup=get_main_menu(user_id in ALLOWED_ADMINS, user))

@dp.message_handler(lambda message: message.text.startswith("🎁"))
async def daily_reward(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("Сначала выбери персонажа.")
        return

    today = str(datetime.now().date())
    if user.get("last_reward_date") == today:
        await message.answer("Ты уже получил награду сегодня.", reply_markup=get_main_menu(user_id in ALLOWED_ADMINS, user))
        return

    result = random.choice(["xp", "coins", "nothing"])
    if result == "xp":
        xp = random.randint(1, 7)
        user = add_xp(user, xp)
        msg = f"Ты получил {xp} XP!"
    elif result == "coins":
        coins = random.randint(1, 7)
        user["coins"] += coins
        msg = f"Ты получил {coins} коинов!"
    else:
        msg = "Сегодня тебе ничего не выпало."

    user["last_reward_date"] = today
    set_user(user_id, user)
    await message.answer(msg, reply_markup=get_main_menu(user_id in ALLOWED_ADMINS, user))

@dp.message_handler(lambda message: message.text == "🆔 Узнать свой ID")
async def show_id(message: types.Message):
    await message.answer(f"Твой Telegram ID: `{message.from_user.id}`", parse_mode='Markdown')

@dp.message_handler(lambda msg: msg.text == "👩‍🏫 Админ-панель")
async def admin_panel(message: types.Message):
    if message.from_user.id not in ALLOWED_ADMINS:
        await message.answer("Доступ запрещён.")
        return
    await message.answer("Введи username учеников через пробел или с новой строки (без @):")
    admin_states[message.from_user.id] = {"mode": "awaiting_usernames"}

@dp.message_handler(lambda msg: admin_states.get(msg.from_user.id, {}).get("mode") == "awaiting_usernames")
async def handle_bulk_usernames(message: types.Message):
    admin_id = message.from_user.id
    input_text = message.text.replace("\n", " ").replace("@", "").strip()
    usernames = [u.strip() for u in input_text.split() if u.strip()]

    found_users = []
    for username in usernames:
        uid, user = find_user_by_username(username)
        if uid and user:
            found_users.append((uid, username, user))

    if not found_users:
        await message.answer("Ни одного ученика не найдено.")
        admin_states.pop(admin_id, None)
        return

    text_lines = [f"Найдено {len(found_users)} учеников:"]
    for _, username, user in found_users:
        text_lines.append(
            f"@{username}: уровень {user['level']}, XP: {user['xp']}, коины: {user['coins']}, школа: {user['school_level']}"
        )

    admin_states[admin_id] = {
        "mode": "bulk_selected",
        "students": found_users
    }

    await message.answer(
        "\n".join(text_lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("✅ Начислить XP и коины всем", callback_data="admin_bulk_reward")],
            [InlineKeyboardButton("❌ Списать коины у всех", callback_data="admin_bulk_deduct")]
        ])
    )

@dp.callback_query_handler(lambda c: c.data in ["admin_bulk_reward", "admin_bulk_deduct"])
async def handle_bulk_action(callback: types.CallbackQuery):
    admin_id = callback.from_user.id
    state = admin_states.get(admin_id)
    if not state or state["mode"] != "bulk_selected":
        await callback.answer("Ошибка состояния.")
        return

    students = state["students"]

    if callback.data == "admin_bulk_reward":
        for uid, _, user in students:
            coins = 10 + user["level"] * 5 + user["school_level"] * 5
            user["coins"] += coins
            user = add_xp(user, 10)
            set_user(uid, user)
            try:
                await bot.send_message(uid, f"Ты получил +10 XP и +{coins} коинов за урок!")
            except:
                pass
        await callback.message.answer("Начисление выполнено всем ученикам.")
        admin_states.pop(admin_id, None)

    elif callback.data == "admin_bulk_deduct":
        state["mode"] = "awaiting_bulk_deduction"
        await bot.send_message(admin_id, "Сколько коинов списать у каждого ученика?")

@dp.message_handler(lambda msg: admin_states.get(msg.from_user.id, {}).get("mode") == "awaiting_bulk_deduction")
async def handle_bulk_deduction_amount(message: types.Message):
    admin_id = message.from_user.id
    state = admin_states.get(admin_id)
    students = state["students"]

    try:
        amount = int(message.text.strip())
    except:
        await message.answer("Нужно ввести число.")
        return

    for uid, _, user in students:
        user["coins"] = max(0, user["coins"] - amount)
        set_user(uid, user)
        try:
            await bot.send_message(uid, f"У тебя списали {amount} коинов.")
        except:
            pass

    await message.answer(f"У всех учеников списано {amount} коинов.")
    admin_states.pop(admin_id, None)

from shop_data import shop_items

@dp.message_handler(lambda message: message.text == "🛒 Магазин улучшений")
async def open_shop(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("Сначала выбери персонажа.")
        return

    for item_id, item in shop_items.items():
        text = f"{item['name']}\nЦена: {item['price']} коинов\n{item['description']}"
        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Купить", callback_data=f"buy_{item_id}")
        )
        try:
            photo = InputFile(item["image"])
            await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
        except:
            await message.answer(text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("buy_"))
async def buy_item(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user = get_user(user_id)
    if not user:
        await callback_query.answer("Сначала выбери персонажа.")
        return

    item_id = callback_query.data.split("_", 1)[1]
    item = shop_items.get(item_id)
    if not item:
        await callback_query.answer("Предмет не найден.")
        return

    if item_id in user.get("items", []):
        await callback_query.answer("Ты уже купил этот предмет.")
        return

    if user["coins"] < item["price"]:
        await callback_query.answer("Недостаточно коинов.")
        return

    user["coins"] -= item["price"]
    user.setdefault("items", []).append(item_id)
    set_user(user_id, user)

    await callback_query.answer(f"Ты купил: {item['name']}!")
    await bot.send_message(user_id, f"Поздравляем с покупкой!\n{item['name']} теперь твой.", reply_markup=get_main_menu(user_id in ALLOWED_ADMINS, user))

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
