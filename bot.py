import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN, MAIN_ADMIN
from database import Database

# Logging sozlash
logging.basicConfig(level=logging.INFO)

# Bot va dispatcher yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()
scheduler = AsyncIOScheduler()

# Admin tekshirish
async def is_admin(user_id: int) -> bool:
    if user_id == MAIN_ADMIN:
        return True
    admins = await db.get_admins()
    return user_id in admins

# Majburiy obuna tekshirish
async def check_subscription(user_id: int) -> bool:
    if not await db.get_setting('force_subscribe'):
        return True
        
    channels = await db.get_channels()
    for channel in channels:
        try:
            member = await bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            continue
    return True

# Start buyrug'i
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    fullname = message.from_user.full_name
    
    await db.add_user(user_id, username, fullname)
    
    # Yangi foydalanuvchi haqida adminga xabar
    if await db.get_setting('notification_new_user'):
        admin_msg = f"Yangi foydalanuvchi!\n\nID: {user_id}\nUsername: @{username}\nIsm: {fullname}"
        await bot.send_message(MAIN_ADMIN, admin_msg)
    
    welcome_text = "Kinolar botiga xush kelibsiz! Kino kodini yuboring."
    await message.answer(welcome_text)

# Kino kodi bilan ishlash
@dp.message(lambda message: message.text and message.text.isdigit())
async def process_movie_code(message: types.Message):
    user_id = message.from_user.id
    code = int(message.text)
    
    if not await check_subscription(user_id):
        channels = await db.get_channels()
        buttons = []
        for channel in channels:
            buttons.append([InlineKeyboardButton(
                text=f"📢 {channel}",
                url=f"https://t.me/{channel}"
            )])
        buttons.append([InlineKeyboardButton(
            text="✅ Tasdiqlash",
            callback_data="check_subscription"
        )])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:", reply_markup=markup)
        return
    
    movie = await db.get_movie(code)
    if not movie:
        await message.answer("⚠️ Bunday kodli kino topilmadi!")
        return
        
    code, title, format, language, file_id, views, is_deleted = movie
    
    caption = f"🎬 {title}\n"
    caption += f"📝 Kod: {code}\n"
    caption += f"📀 Format: {format}\n"
    caption += f"🗣 Til: {language}\n"
    caption += f"👁 Ko'rishlar: {views}"
    
    await bot.send_video(
        chat_id=user_id,
        video=file_id,
        caption=caption
    )
    
    await db.increment_views(code)

# Admin buyruqlari
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
        
    stats = await db.get_stats()
    admin_text = "📊 Bot statistikasi:\n\n"
    admin_text += f"👥 Foydalanuvchilar: {stats['users']}\n"
    admin_text += f"🎬 Kinolar: {stats['movies']}\n"
    admin_text += f"👁 Umumiy ko'rishlar: {stats['total_views']}\n\n"
    admin_text += "Admin buyruqlari:\n"
    admin_text += "/addmovie - Kino qo'shish\n"
    admin_text += "/deletemovie - Kino o'chirish\n"
    admin_text += "/setchannels - Majburiy obuna kanallarini sozlash\n"
    admin_text += "/msgall - Barchaga xabar yuborish\n"
    admin_text += "/msguser - Foydalanuvchiga xabar yuborish\n"
    admin_text += "/setadmin - Admin qo'shish\n"
    admin_text += "/removeadmin - Adminni o'chirish\n"
    admin_text += "/listads - Reklamalar ro'yxati"
    
    await message.answer(admin_text)

# Kino qo'shish
@dp.message(Command("addmovie"))
async def cmd_add_movie(message: types.Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
        
    await message.answer("Kino videosini yuboring")
    dp.register_message_handler(process_movie_video, content_types=['video'], state=None)

async def process_movie_video(message: types.Message):
    video = message.video
    file_id = video.file_id
    
    await message.answer("Kino nomini kiriting:")
    dp.register_message_handler(
        process_movie_title,
        lambda m: True,
        state=None,
        user_data={'file_id': file_id}
    )

# Xatolar bilan ishlash
async def handle_error(update: types.Update, exception: Exception):
    error_msg = f"Xatolik yuz berdi!\n\nUpdate: {update}\n\nError: {exception}"
    await bot.send_message(MAIN_ADMIN, error_msg)
    logging.error(f"Update: {update} \n{exception}")

# Asosiy ishga tushirish
async def main():
    await db.create_tables()
    scheduler.start()
    
    # Super adminni qo'shish
    await db.add_admin(MAIN_ADMIN)
    
    # Xato handlerini qo'shish  
    dp.errors.register(handle_error)
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
