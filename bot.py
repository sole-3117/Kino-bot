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

# Obuna tekshirish callback
@dp.callback_query(lambda c: c.data == 'check_subscription')
async def callback_check_subscription(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    
    if await check_subscription(user_id):
        await callback_query.message.delete()
        await bot.send_message(user_id, "✅ Obuna tasdiqlandi! Kino kodini yuboring.")
    else:
        await callback_query.answer("❌ Siz hali kanallarga obuna bo'lmagansiz!", show_alert=True)

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
    if not await is_admin(message.from_user.id):
        return
    await message.answer("Kino videosini yuboring.")

# Video qabul qilish
@dp.message(content_types=['video'])
async def process_movie_video(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
        
    file_id = message.video.file_id
    await message.answer("Kino nomini kiriting:")
    
    # State'ga file_id ni saqlash
    state = dp.current_state(user=message.from_user.id)
    await state.update_data(file_id=file_id)

# Kino nomini qabul qilish
@dp.message()
async def process_movie_title(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
        
    state = dp.current_state(user=message.from_user.id)
    data = await state.get_data()
    
    if 'file_id' not in data:
        return
        
    file_id = data['file_id']
    title = message.text
    
    code = await db.add_movie(
        title=title,
        format="MP4",
        language="O'zbek",
        file_id=file_id
    )
    
    await message.answer(f"✅ Kino qo'shildi!\nKod: {code}")
    await state.finish()

# Kino o'chirish
@dp.message(Command("deletemovie"))
async def cmd_delete_movie(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    
    args = message.get_args()
    if not args or not args.isdigit():
        await message.answer("❌ Kino kodini kiriting:\n/deletemovie {kod}")
        return
        
    code = int(args)
    movie = await db.get_movie(code)
    
    if not movie:
        await message.answer("⚠️ Bunday kodli kino topilmadi!")
        return
        
    await db.delete_movie(code)
    await message.answer(f"✅ {code} kodli kino o'chirildi!")

# Kanallarni sozlash
@dp.message(Command("setchannels"))
async def cmd_set_channels(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
        
    args = message.get_args().split()
    if not args:
        channels = await db.get_channels()
        channels_text = "\n".join(f"@{channel}" for channel in channels) or "Bo'sh"
        await message.answer(
            f"Majburiy obuna kanallari:\n{channels_text}\n\n"
            "Kanal qo'shish: /setchannels add username\n"
            "Kanalni o'chirish: /setchannels remove username"
        )
        return
        
    action = args[0].lower()
    if len(args) != 2:
        await message.answer("❌ Noto'g'ri format!")
        return
        
    username = args[1].replace("@", "")
    
    if action == "add":
        await db.add_channel(username)
        await message.answer(f"✅ @{username} kanali qo'shildi!")
    elif action == "remove":
        await db.remove_channel(username)
        await message.answer(f"✅ @{username} kanali o'chirildi!")
    else:
        await message.answer("❌ Noto'g'ri buyruq!")

# Barchaga xabar yuborish
@dp.message(Command("msgall"))
async def cmd_message_all(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
        
    text = message.get_args()
    if not text:
        await message.answer("❌ Xabar matnini kiriting:\n/msgall {matn}")
        return
        
    users = await db.get_all_users()
    success = 0
    fail = 0
    
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            success += 1
        except:
            fail += 1
        await asyncio.sleep(0.05)
    
    await message.answer(f"✅ Xabar yuborildi:\n"
                        f"Muvaffaqiyatli: {success}\n"
                        f"Muvaffaqiyatsiz: {fail}")

# Foydalanuvchiga xabar yuborish
@dp.message(Command("msguser"))
async def cmd_message_user(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
        
    args = message.get_args().split(maxsplit=1)
    if len(args) != 2:
        await message.answer("❌ Format:\n/msguser {user_id} {matn}")
        return
        
    try:
        user_id = int(args[0])
        text = args[1]
        
        await bot.send_message(user_id, text)
        await message.answer("✅ Xabar yuborildi!")
    except:
        await message.answer("❌ Xabar yuborilmadi!")

# Admin qo'shish
@dp.message(Command("setadmin"))
async def cmd_set_admin(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
        
    args = message.get_args()
    if not args or not args.isdigit():
        await message.answer("❌ Format:\n/setadmin {user_id}")
        return
        
    user_id = int(args)
    await db.add_admin(user_id)
    await message.answer(f"✅ {user_id} admin qilindi!")

# Adminni o'chirish
@dp.message(Command("removeadmin"))
async def cmd_remove_admin(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
        
    args = message.get_args()
    if not args or not args.isdigit():
        await message.answer("❌ Format:\n/removeadmin {user_id}")
        return
        
    user_id = int(args)
    if user_id == MAIN_ADMIN:
        await message.answer("❌ Asosiy adminni o'chirib bo'lmaydi!")
        return
        
    await db.remove_admin(user_id)
    await message.answer(f"✅ {user_id} adminlikdan olindi!")

# Reklamalarni boshqarish
@dp.message(Command("listads"))
async def cmd_list_ads(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
        
    ads = await db.get_scheduled_ads()
    if not ads:
        await message.answer("Rejalashtilgan reklamalar yo'q!")
        return
        
    text = "📢 Reklamalar:\n\n"
    for ad in ads:
        ad_id, _, ad_text, button_text, _, schedule_time, repeat_count = ad
        text += f"ID: {ad_id}\n"
        text += f"Matn: {ad_text[:50]}...\n"
        text += f"Tugma: {button_text}\n"
        text += f"Vaqt: {schedule_time}\n"
        text += f"Takrorlanish: {repeat_count}\n\n"
    
    await message.answer(text)

# Reklamani yuborish
async def send_ad(ad_id: int, image_file_id: str, text: str, button_text: str, button_url: str):
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=button_text, url=button_url)
    ]])
    
    users = await db.get_all_users()
    success = 0
    fail = 0
    
    for user_id in users:
        try:
            await bot.send_photo(
                chat_id=user_id,
                photo=image_file_id,
                caption=text,
                reply_markup=markup
            )
            success += 1
        except:
            fail += 1
        await asyncio.sleep(0.05)
    
    await bot.send_message(
        MAIN_ADMIN,
        f"Reklama yuborildi:\n✅ Muvaffaqiyatli: {success}\n❌ Muvaffaqiyatsiz: {fail}"
    )

# Reklamalarni rejalashtirish
async def schedule_ads():
    ads = await db.get_scheduled_ads()
    for ad in ads:
        ad_id, image_file_id, text, button_text, button_url, schedule_time, repeat_count = ad
        
        if repeat_count > 0:
            scheduler.add_job(
                send_ad,
                'date',
                run_date=datetime.fromisoformat(schedule_time),
                args=[ad_id, image_file_id, text, button_text, button_url]
            )
            
            await db.update_ad_count(ad_id, repeat_count - 1)

# Xatolarni boshqarish
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
