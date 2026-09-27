import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import aiohttp

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8220814941:AAHVtTIJOHReLcmhtMG9iH3WqxWgpmjHEbU"
ADMIN_IDS = [8318241400]

# Majburiy kanallar (o'zingiznikiga o'zgartiring)
REQUIRED_CHANNELS = [
    {"id": -1001234567890, "link": "https://t.me/your_channel1", "name": "Anime News"},
    {"id": -1009876543210, "link": "https://t.me/your_channel2", "name": "Anime Community"},
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ==================== DATABASE ====================
async def init_db():
    async with aiosqlite.connect("anime_bot.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def add_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect("anime_bot.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )
        await db.commit()

async def get_users_count():
    async with aiosqlite.connect("anime_bot.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_all_users():
    async with aiosqlite.connect("anime_bot.db") as db:
        async with db.execute("SELECT user_id FROM users WHERE is_banned = 0") as cursor:
            return [row[0] for row in await cursor.fetchall()]

# ==================== KEYBOARDS ====================
def main_menu():
    keyboard = [
        [
            InlineKeyboardButton(text="🔍 Anime Qidirish", callback_data="search_anime"),
            InlineKeyboardButton(text="🎲 Tasodifiy Anime", callback_data="random_anime")
        ],
        [
            InlineKeyboardButton(text="🏆 Top Anime", callback_data="top_anime"),
            InlineKeyboardButton(text="📺 Ongoing", callback_data="ongoing")
        ],
        [
            InlineKeyboardButton(text="👤 Profil", callback_data="profile"),
            InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_main")]
    ])

def subscribe_keyboard():
    buttons = []
    for ch in REQUIRED_CHANNELS:
        buttons.append([InlineKeyboardButton(text=f"📢 {ch['name']}", url=ch['link'])])
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ==================== MAJBURIY OBUNA ====================
async def check_subscription(user_id: int) -> bool:
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(channel["id"], user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

# ==================== API FUNKSIYALAR ====================
async def search_anime(query: str, limit: int = 8):
    url = f"https://api.jikan.moe/v4/anime?q={query}&limit={limit}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", [])
            return []

async def get_random_anime():
    url = "https://api.jikan.moe/v4/random/anime"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data")
            return None

async def get_top_anime(limit: int = 10):
    url = f"https://api.jikan.moe/v4/top/anime?limit={limit}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", [])
            return []

def format_anime(anime: dict) -> str:
    title = anime.get("title", "Noma'lum")
    title_jp = anime.get("title_japanese", "")
    score = anime.get("score") or "—"
    episodes = anime.get("episodes") or "?"
    status = anime.get("status", "—")
    year = anime.get("year") or "—"
    genres = ", ".join([g["name"] for g in anime.get("genres", [])][:4]) or "—"
    synopsis = (anime.get("synopsis") or "Tavsif yo'q")[:280] + "..."

    text = f"""
<b>🎌 {title}</b>
{f'<i>{title_jp}</i>' if title_jp else ''}

⭐ <b>Reyting:</b> {score}
📺 <b>Epizodlar:</b> {episodes}
📅 <b>Yil:</b> {year}
🟢 <b>Status:</b> {status}
🎭 <b>Janr:</b> {genres}

📝 <b>Tavsif:</b>
{synopsis}
"""
    return text.strip()

# ==================== HANDLERS ====================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    await add_user(user.id, user.username, user.full_name)

    if not await check_subscription(user.id):
        await message.answer(
            "<b>🔐 Majburiy obuna</b>\n\n"
            "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:",
            reply_markup=subscribe_keyboard()
        )
        return

    await message.answer(
        f"<b>✨ Assalomu alaykum, {user.first_name}!</b>\n\n"
        "Men professional <b>Anime Bot</b>man 🎌\n"
        "Quyidagi menyudan foydalaning:",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            f"<b>✅ Obuna tasdiqlandi!</b>\n\n"
            f"Xush kelibsiz, {callback.from_user.first_name}!",
            reply_markup=main_menu()
        )
    else:
        await callback.answer("❌ Hali barcha kanallarga obuna bo‘lmadingiz!", show_alert=True)

@dp.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "<b>🏠 Asosiy menyu</b>\n\nQuyidagilardan birini tanlang:",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "search_anime")
async def search_anime_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔍 <b>Anime qidirish</b>\n\nAnime nomini yozing:",
        reply_markup=back_button()
    )
    await state.set_state("waiting_search")

@dp.message(F.text, F.state == "waiting_search")
async def process_search(message: Message, state: FSMContext):
    query = message.text.strip()
    await message.answer("⏳ Qidirilmoqda...")

    results = await search_anime(query)
    if not results:
        await message.answer("❌ Hech narsa topilmadi.", reply_markup=main_menu())
        await state.clear()
        return

    for anime in results[:5]:
        text = format_anime(anime)
        image = anime.get("images", {}).get("jpg", {}).get("large_image_url")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 MyAnimeList", url=anime.get("url", "https://myanimelist.net"))]
        ])
        if image:
            await message.answer_photo(photo=image, caption=text, reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)

    await message.answer("🔍 Yana qidirish uchun menyudan foydalaning:", reply_markup=main_menu())
    await state.clear()

@dp.callback_query(F.data == "random_anime")
async def random_anime_handler(callback: CallbackQuery):
    await callback.message.edit_text("🎲 Tasodifiy anime tanlanmoqda...")
    anime = await get_random_anime()
    if not anime:
        await callback.message.edit_text("❌ Xatolik yuz berdi.", reply_markup=main_menu())
        return

    text = format_anime(anime)
    image = anime.get("images", {}).get("jpg", {}).get("large_image_url")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yana tasodifiy", callback_data="random_anime")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_main")]
    ])
    if image:
        await callback.message.delete()
        await callback.message.answer_photo(photo=image, caption=text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(F.data == "top_anime")
async def top_anime_handler(callback: CallbackQuery):
    await callback.message.edit_text("🏆 Top anime yuklanmoqda...")
    animes = await get_top_anime(10)
    if not animes:
        await callback.message.edit_text("❌ Xatolik.", reply_markup=main_menu())
        return

    text = "<b>🏆 TOP 10 Anime</b>\n\n"
    for i, anime in enumerate(animes, 1):
        score = anime.get("score") or "—"
        text += f"{i}. <b>{anime.get('title')}</b> — ⭐ {score}\n"

    await callback.message.edit_text(text, reply_markup=back_button())

@dp.callback_query(F.data == "ongoing")
async def ongoing_handler(callback: CallbackQuery):
    await callback.message.edit_text("📺 Ongoing anime yuklanmoqda...")
    url = "https://api.jikan.moe/v4/seasons/now?limit=10"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json() if resp.status == 200 else {}
            animes = data.get("data", [])

    if not animes:
        await callback.message.edit_text("❌ Xatolik.", reply_markup=main_menu())
        return

    text = "<b>📺 Hozirgi mavsum (Ongoing)</b>\n\n"
    for i, anime in enumerate(animes, 1):
        text += f"{i}. <b>{anime.get('title')}</b>\n"

    await callback.message.edit_text(text, reply_markup=back_button())

@dp.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery):
    user = callback.from_user
    count = await get_users_count()
    text = f"""
<b>👤 Sizning profilingiz</b>

🆔 ID: <code>{user.id}</code>
👤 Ism: {user.full_name}
📱 Username: @{user.username or 'yo‘q'}

📊 Botdagi jami foydalanuvchilar: <b>{count}</b>
"""
    await callback.message.edit_text(text, reply_markup=back_button())

@dp.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery):
    text = """
<b>ℹ️ Yordam</b>

🔍 <b>Anime Qidirish</b> — anime nomi bo‘yicha qidirish
🎲 <b>Tasodifiy Anime</b> — tasodifiy tavsiya
🏆 <b>Top Anime</b> — eng yuqori reytingdagi animelar
📺 <b>Ongoing</b> — hozir chiqayotgan animelar

Savollar bo‘lsa admin bilan bog‘laning.
"""
    await callback.message.edit_text(text, reply_markup=back_button())

# ==================== ADMIN PANEL ====================
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    count = await get_users_count()
    text = f"""
<b>🛠 Admin Panel</b>

👥 Jami foydalanuvchilar: <b>{count}</b>

Buyruqlar:
/broadcast - Hammaga xabar yuborish
/stats - Statistika
"""
    await message.answer(text)

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    count = await get_users_count()
    await message.answer(f"📊 Jami foydalanuvchilar: <b>{count}</b>")

@dp.message(Command("broadcast"))
async def broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("📢 Yubormoqchi bo‘lgan xabaringizni yozing:")
    await state.set_state("waiting_broadcast")

@dp.message(F.state == "waiting_broadcast")
async def process_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    users = await get_all_users()
    success = 0
    fail = 0

    await message.answer(f"🚀 Yuborilmoqda... ({len(users)} ta foydalanuvchi)")

    for user_id in users:
        try:
            await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1

    await message.answer(f"✅ Yuborildi: {success}\n❌ Xato: {fail}")
    await state.clear()

# ==================== START ====================
async def main():
    await init_db()
    logger.info("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
