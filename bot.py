import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import os

# TOKEN va ADMIN_ID
TOKEN = 'BOT_TOKEN'
ADMIN_ID = 615155352

bot = telebot.TeleBot(TOKEN)

# Fayl yo'llari
if not os.path.exists("data"): os.mkdir("data")
MOVIES_FILE = "data/movies.json"
CHANNELS_FILE = "data/channels.json"
ADS_FILE = "data/ads.json"
USERS_FILE = "data/users.json"

# Fayllarni yaratish
def ensure_file(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f)

ensure_file(MOVIES_FILE, {})
ensure_file(CHANNELS_FILE, [])
ensure_file(ADS_FILE, [])
ensure_file(USERS_FILE, [])

# JSON fayllarni o'qish/saqlash
def load(path):
    with open(path) as f: return json.load(f)
def save(path, data):
    with open(path, "w") as f: json.dump(data, f, indent=2)

# Majburiy obuna
def check_subscription(user_id):
    channels = load(CHANNELS_FILE)
    for ch in channels:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

# /start
@bot.message_handler(commands=["start"])
def start(msg):
    user_id = msg.from_user.id
    users = load(USERS_FILE)
    users[str(user_id)] = True
    save(USERS_FILE, users)

    if not check_subscription(user_id):
        channels = load(CHANNELS_FILE)
        text = "🔐 Botdan foydalanish uchun quyidagilarga obuna bo‘ling:\n\n"
        for ch in channels:
            text += f"👉 {ch}\n"
        text += "\n✅ Obunani tugatgach, qayta /start bosing."
        return bot.send_message(user_id, text)

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎬 Kino qo‘shish", callback_data="add_movie"),
        InlineKeyboardButton("📛 Obuna kanal", callback_data="add_channel")
    )
    if user_id == ADMIN_ID:
        bot.send_message(user_id, "👋 Xush kelibsiz! Admin panel:", reply_markup=markup)
    else:
        bot.send_message(user_id, "🎬 Kino kodi yuboring (masalan: `1`)")

# Inline tugmalar
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    cid = call.message.chat.id
    if call.data == "add_movie":
        if cid != ADMIN_ID: return
        bot.send_message(cid, "🎬 Kino kodi?")
        bot.register_next_step_handler(call.message, get_movie_code)
    elif call.data == "add_channel":
        if cid != ADMIN_ID: return
        bot.send_message(cid, "📛 Obuna kanalini @ bilan yuboring:")
        bot.register_next_step_handler(call.message, save_channel)

# Kino qo‘shish ketma-ket
def get_movie_code(msg):
    code = msg.text.strip()
    bot.send_message(msg.chat.id, "📛 Kino nomi?")
    bot.register_next_step_handler(msg, lambda m: get_movie_name(m, code))

def get_movie_name(msg, code):
    name = msg.text.strip()
    bot.send_message(msg.chat.id, "🎥 Kino videosini yuboring:")
    bot.register_next_step_handler(msg, lambda m: save_movie(m, code, name))

def save_movie(msg, code, name):
    if not msg.video:
        return bot.send_message(msg.chat.id, "❌ Video yuboring.")
    video_id = msg.video.file_id
    movies = load(MOVIES_FILE)
    movies[code] = {"name": name, "video_id": video_id}
    save(MOVIES_FILE, movies)
    bot.send_message(msg.chat.id, f"✅ '{name}' kodi bilan saqlandi.")

# Obuna kanal saqlash
def save_channel(msg):
    ch = msg.text.strip()
    channels = load(CHANNELS_FILE)
    if ch not in channels:
        channels.append(ch)
        save(CHANNELS_FILE, channels)
        bot.send_message(msg.chat.id, f"✅ Kanal qo‘shildi: {ch}")
    else:
        bot.send_message(msg.chat.id, "⚠️ Bu kanal allaqachon ro‘yxatda.")

# Kino kodni qabul qilish
@bot.message_handler(func=lambda m: True)
def movie_handler(msg):
    user_id = msg.from_user.id
    if not check_subscription(user_id):
        return start(msg)

    code = msg.text.strip()
    movies = load(MOVIES_FILE)
    ads = load(ADS_FILE)

    if code in movies:
        # Reklama chiqarish
        if ads:
            ad = ads[0]
            bot.send_photo(user_id, ad["photo"], caption=ad["text"])
        # Kino yuborish
        movie = movies[code]
        bot.send_video(user_id, movie["video_id"], caption=movie["name"])
    else:
        bot.send_message(user_id, "❌ Bunday kino topilmadi.")

# Reklama qo‘shish
@bot.message_handler(commands=["addad"])
def add_ad(msg):
    if msg.from_user.id != ADMIN_ID: return
    bot.send_message(msg.chat.id, "📢 Reklama matnini yuboring:")
    bot.register_next_step_handler(msg, get_ad_text)

def get_ad_text(msg):
    text = msg.text.strip()
    bot.send_message(msg.chat.id, "🖼 Rasm yuboring:")
    bot.register_next_step_handler(msg, lambda m: save_ad(m, text))

def save_ad(msg, text):
    if not msg.photo:
        return bot.send_message(msg.chat.id, "❌ Rasm kerak.")
    photo = msg.photo[-1].file_id
    ads = load(ADS_FILE)
    ads.append({"text": text, "photo": photo})
    save(ADS_FILE, ads)
    bot.send_message(msg.chat.id, "✅ Reklama saqlandi.")

# Reklama o‘chirish
@bot.message_handler(commands=["delad"])
def delete_ad(msg):
    if msg.from_user.id != ADMIN_ID: return
    save(ADS_FILE, [])
    bot.send_message(msg.chat.id, "❌ Barcha reklamalar o‘chirildi.")

# Botni ishga tushurish
print("🤖 Kino bot ishga tushdi...")
bot.infinity_polling()
