import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, Text
from aiogram import Router
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import Database
from utils import human_time

# Env yuklash
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MAIN_ADMIN = int(os.getenv("MAIN_ADMIN", "0"))

if not BOT_TOKEN or MAIN_ADMIN == 0:
    raise RuntimeError("BOT_TOKEN yoki MAIN_ADMIN .env da to'ldirilmagan!")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot yaratish
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
db = Database()
scheduler = AsyncIOScheduler()

# --- Helperlar ---
async def is_admin(user_id: int) -> bool:
    if user_id == MAIN_ADMIN:
        return True
    admins = await db.get_admins()
    return user_id in admins

async def require_subscription_markup():
    channels = await db.get_channels()
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(text=f"📢 @{ch}", url=f"https://t.me/{ch}")])
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Foydalanuvchi komandalar ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    await db.add_user(user.id, user.username or "", user.full_name or "")
    if await db.get_setting('notification_new_user'):
        try:
            await bot.send_message(MAIN_ADMIN, f"Yangi foydalanuvchi: {user.full_name} (@{user.username}) — {user.id}")
        except Exception:
            pass
    await message.answer("Assalomu alaykum! Kino-kod yuboring yoki /help bilan yordam oling.")

@router.message(Command("help"))
async def cmd_help(message: Message):
    txt = (
        "/help — yordam\n"
        "Kino kodini yuboring (faqat raqamlar yoki kod formatiga mos)\n"
        "/search <text> — nom bo‘yicha qidirish\n"
        "/fav — sevimlilarni ko‘rish (login kerak)\n"
    )
    await message.answer(txt)

@router.message(Command("search"))
async def cmd_search(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Qidiruv uchun so‘z kiriting: /search Inception")
        return
    q = args[1].strip()
    results = await db.search_movies(q)
    if not results:
        await message.reply("Hech narsa topilmadi.")
        return
    for movie in results:
        code, title, fmt, lang, file_id, views, is_deleted = movie
        await message.reply(f"🎬 {title}\n🆔 {code}\n📀 {fmt}  |  {lang}\n👁 {views}")

@router.message(lambda m: m.text and m.text.isdigit())
async def handle_code(message: Message):
    user_id = message.from_user.id
    # Majburiy obuna tekshiruvi
    if await db.get_setting('force_subscribe') == 'true':
        channels = await db.get_channels()
        if channels:
            try:
                ok = True
                for ch in channels:
                    member = await bot.get_chat_member(f"@{ch}", user_id)
                    if member.status in ['left', 'kicked']:
                        ok = False
                        break
                if not ok:
                    markup = await require_subscription_markup()
                    await message.answer("Botdan foydalanish uchun kanal(lar)ga obuna bo'ling:", reply_markup=markup)
                    return
            except Exception:
                # agar kanalni tekshirishda xato bo'lsa, davom etish uchun pass
                pass

    code = int(message.text)
    movie = await db.get_movie(code)
    if not movie:
        await message.reply("⚠️ Bunday kodli kino topilmadi.")
        return
    code, title, fmt, lang, file_id, views, is_deleted = movie
    caption = f"🎬 {title}\n🆔 {code}\n📀 {fmt}\n🗣 {lang}\n👁 {views}"
    try:
        # agar video bo'lsa yuborish, aks holda fayl_id sifatida yuborish
        await bot.send_video(chat_id=user_id, video=file_id, caption=caption)
    except Exception:
        # fallback: oddiy xabar bilan link/ma'lumot
        await message.answer(caption + "\n(Fayl yuborilmadi — file_id yoki link noto'g'ri)")
    await db.increment_views(code)

# --- Admin komandalar ---
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("🚫 Siz admin emassiz.")
        return
    stats = await db.get_stats()
    txt = (
        f"📊 Statistika:\n👥 Foydalanuvchilar: {stats['users']}\n"
        f"🎬 Kinolar: {stats['movies']}\n👁 Jami ko'rishlar: {stats['total_views']}\n\n"
        "Admin buyruqlari:\n"
        "/addmovie — kino qo'shish\n"
        "/delmovie <code> — kino o'chirish\n"
        "/listmovies — kinolar ro'yxati\n"
        "/broadcast — hamma foydalanuvchilarga xabar yuborish\n"
        "/setchannel <username> — kanal qo'shish (majburiy obuna)\n"
        "/rmchannel <username> — kanalni o'chirish\n"
        "/addadmin <user_id> — admin qo'shish\n"
        "/rmadmin <user_id> — admin o'chirish\n"
        "/set <key> <value> — sozlamani o'zgartirish\n"
    )
    await message.answer(txt)

@router.message(Command("addmovie"))
async def cmd_addmovie(message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("🚫 Siz admin emassiz.")
        return
    # simple flow: admin yuboradi -> keyingi xabarda nom; implement minimal interactive flow
    await message.answer("📥 Kino qo'shish: Quyidagi formatda yuboring:\nTitle | format | language | file_id\nMasalan:\nInception | mp4 | English | file_123")

@router.message()
async def admin_addmovie_flow(message: Message):
    # Agar admin va format mos bo'lsa, qo'shamiz
    if not await is_admin(message.from_user.id):
        return
    text = message.text
    if "|" not in text:
        return
    parts = [p.strip() for p in text.split("|")]
    if len(parts) != 4:
        return
    title, fmt, lang, file_id = parts
    code = await db.add_movie(title, fmt, lang, file_id)
    await message.reply(f"✅ Kino qo'shildi. Kod: {code}")

@router.message(Command("delmovie"))
async def cmd_delmovie(message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("🚫 Siz admin emassiz.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Foydalanish: /delmovie <code>")
        return
    try:
        code = int(args[1])
        await db.delete_movie(code)
        await message.reply("✅ Kino o'chirildi.")
    except Exception:
        await message.reply("Kod noto'g'ri yoki xato yuz berdi.")

@router.message(Command("listmovies"))
async def cmd_listmovies(message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("🚫 Siz admin emassiz.")
        return
    movies = await db.get_all_movies()
    if not movies:
        await message.reply("Kinolar topilmadi.")
        return
    text = "🎬 Kinolar ro'yxati:\n\n"
    for m in movies:
        text += f"{m[0]} — {m[1]} ({m[2]} | {m[3]}) views:{m[5]}\n"
    await message.reply(text)

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("🚫 Siz admin emassiz.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Foydalanish: /broadcast <xabar>")
        return
    text = args[1]
    users = await db.get_all_users()
    sent = 0
    for uid in users:
        try:
            await bot.send_message(uid, text)
            sent += 1
            await asyncio.sleep(0.05)  # rate limit uchun kichik tanaffus
        except Exception:
            continue
    await message.reply(f"✅ Xabar yuborildi: {sent}/{len(users)} ga")

@router.message(Command("setchannel"))
async def cmd_setchannel(message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("🚫 Siz admin emassiz.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Foydalanish: /setchannel <channel_username_without_@>")
        return
    ch = args[1].lstrip("@")
    await db.add_channel(ch)
    await message.reply(f"✅ Kanal @{ch} qo'shildi (majburiy obuna).")

@router.message(Command("rmchannel"))
async def cmd_rmchannel(message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("🚫 Siz admin emassiz.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Foydalanish: /rmchannel <channel_username_without_@>")
        return
    ch = args[1].lstrip("@")
    await db.remove_channel(ch)
    await message.reply(f"✅ Kanal @{ch} o'chirildi.")

@router.message(Command("addadmin"))
async def cmd_addadmin(message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("🚫 Siz admin emassiz.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Foydalanish: /addadmin <user_id>")
        return
    try:
        uid = int(args[1])
        await db.add_admin(uid)
        await message.reply("✅ Admin qo'shildi.")
    except:
        await message.reply("ID noto'g'ri.")

@router.message(Command("rmadmin"))
async def cmd_rmadmin(message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("🚫 Siz admin emassiz.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Foydalanish: /rmadmin <user_id>")
        return
    try:
        uid = int(args[1])
        await db.remove_admin(uid)
        await message.reply("✅ Admin o'chirildi.")
    except:
        await message.reply("Xato yuz berdi.")

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("🚫 Siz admin emassiz.")
        return
    s = await db.get_stats()
    await message.reply(f"👥 {s['users']}  🎬 {s['movies']}  👁 {s['total_views']}")

# include router
dp.include_router(router)

# Scheduler misol uchun reklamalarni yuborish (oddiy)
async def send_scheduled_ads():
    ads = await db.get_scheduled_ads()
    users = await db.get_all_users()
    for ad in ads:
        ad_id, image_file_id, text, btn_text, btn_url, schedule_time, repeat_count = ad
        for uid in users:
            try:
                if image_file_id:
                    await bot.send_photo(uid, image_file_id, caption=text)
                else:
                    await bot.send_message(uid, text)
            except Exception:
                continue
        # repeat_count kamaytirish
        if repeat_count and repeat_count > 0:
            await db.update_ad_count(ad_id, repeat_count - 1)

async def main():
    await db.create_tables()
    # super adminni jadvalga qo'shish
    await db.add_admin(MAIN_ADMIN)
    # scheduler ishga tushirish (har 1 soatda misol)
    scheduler.add_job(send_scheduled_ads, 'interval', hours=1)
    scheduler.start()
    logger.info("Bot ishga tushmoqda...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())