import { useState } from “react”;

const tabs = [“Integratsiya Rejasi”, “ai_agent.py”, “bot_parser.py”, “db_helper.py”, “scheduler.py”];

const plan = [
{
step: “1”,
color: “#6366f1”,
title: “AI Agent — Metadata yig’ish”,
desc: “TMDB dan kino ma’lumotlari + Claude API bilan o’zbekcha boyitish”,
note: “⚠️ Video file_id yo’q — metadata only (nom, yil, reyting, tavsif, poster)”
},
{
step: “2”,
color: “#0ea5e9”,
title: “Guruhga formatlangan xabar”,
desc: “Mavjud /add formatiga mos #AUTO_MOVIE tegi bilan yuboriladi”,
note: “✅ python-telegram-bot 20.7 ga moslashtirilgan”
},
{
step: “3”,
color: “#10b981”,
title: “Bot Parser — xabarni ushlash”,
desc: “Kino Bot guruh xabarini parse qiladi va DB ga yozadi”,
note: “✅ Mavjud movies jadvaliga to’g’ridan-to’g’ri yozadi”
},
{
step: “4”,
color: “#f59e0b”,
title: “Admin Video Qo’shish (yarim-avtomatik)”,
desc: “/add_video [kod] buyrug’i bilan admin faqat videoni ulaydi”,
note: “🎯 AI metadata + Admin video = To’liq yozuv”
}
];

const agentCode = `# ai_agent.py

# Kino Bot loyhasiga qo’shiladi — alohida fayl

# python-telegram-bot 20.7 uchun moslashtirilgan

import asyncio, httpx, json, os, logging
from anthropic import AsyncAnthropic
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format=”%(asctime)s — %(message)s”)
logger = logging.getLogger(**name**)

TMDB_KEY   = os.getenv(“TMDB_API_KEY”)
BOT_TOKEN  = os.getenv(“AGENT_BOT_TOKEN”)   # Alohida agent bot tokeni
GROUP_ID   = int(os.getenv(“AUTO_GROUP_ID”)) # Maxfiy guruh ID

claude = AsyncAnthropic(api_key=os.getenv(“ANTHROPIC_API_KEY”))
bot    = Bot(token=BOT_TOKEN)

# ─────────────────────────────────────────

# 1. TMDB: Trend + Top Rated kinolar

# ─────────────────────────────────────────

async def fetch_movies(endpoint=“trending/movie/week”, page=1) -> list:
url = f”https://api.themoviedb.org/3/{endpoint}”
params = {“api_key”: TMDB_KEY, “language”: “en-US”, “page”: page}
async with httpx.AsyncClient(timeout=15) as client:
r = await client.get(url, params=params)
r.raise_for_status()
return r.json().get(“results”, [])

# ─────────────────────────────────────────

# 2. Claude: Ma’lumotni boyitish

# ─────────────────────────────────────────

async def enrich_with_claude(movie: dict) -> dict | None:
poster = f”https://image.tmdb.org/t/p/w500{movie.get(‘poster_path’,’’)}”
prompt = f””“Quyidagi kino uchun faqat JSON qaytargil (hech qanday izoh yoki markdown yo’q):

Kino ma’lumotlari:

- Nomi: {movie.get(‘title’, ‘’)}
- Yil: {str(movie.get(‘release_date’, ‘’))[:4]}
- Reyting: {movie.get(‘vote_average’, 0)}
- Tavsif (inglizcha): {movie.get(‘overview’, ‘’)[:300]}
- Janrlar (ID): {movie.get(‘genre_ids’, [])}

JSON format:
{{
“title_uz”: “O’zbek yoki rus translit nomi”,
“title_original”: “{movie.get(‘title’, ‘’)}”,
“year”: “{str(movie.get(‘release_date’,’’))[:4]}”,
“rating”: {round(movie.get(‘vote_average’, 0), 1)},
“quality”: “HD”,
“language”: “Uzbek”,
“genre”: “Action|Drama|Thriller (genre_ids asosida, | bilan ajrat)”,
“description”: “O’zbek tilida 2-3 jumla tavsif”,
“poster_url”: “{poster}”,
“tmdb_id”: {movie.get(‘id’, 0)}
}}”””

```
try:
    resp = await claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    text = resp.content[0].text.strip()
    # JSON ni tozalash
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)
except (json.JSONDecodeError, Exception) as e:
    logger.error(f"Claude xato [{movie.get('title')}]: {e}")
    return None
```

# ─────────────────────────────────────────

# 3. Guruhga formatlangan xabar yuborish

# ─────────────────────────────────────────

async def send_movie_to_group(data: dict, source: str = “TREND”) -> bool:
msg = (
f”🎬 #AUTO_MOVIE #{source}\n”
f”{‘━’ * 20}\n”
f”📌 Nomi: {data[‘title_uz’]}\n”
f”🌐 Original: {data[‘title_original’]}\n”
f”🎭 Janr: {data[‘genre’]}\n”
f”📺 Sifat: {data[‘quality’]}\n”
f”🌍 Til: {data[‘language’]}\n”
f”⭐ Reyting: {data[‘rating’]}/10\n”
f”📅 Yil: {data[‘year’]}\n”
f”📝 Tavsif: {data[‘description’]}\n”
f”🖼 Poster: {data[‘poster_url’]}\n”
f”🔑 TMDB: {data[‘tmdb_id’]}\n”
f”#PENDING_VIDEO”
)
try:
await bot.send_message(chat_id=GROUP_ID, text=msg)
logger.info(f”✅ Yuborildi: {data[‘title_uz’]}”)
return True
except TelegramError as e:
logger.error(f”❌ Telegram xato: {e}”)
return False

# ─────────────────────────────────────────

# 4. Asosiy funksiya

# ─────────────────────────────────────────

async def discover_and_post(limit: int = 5, source: str = “TREND”):
endpoint_map = {
“TREND”:   “trending/movie/week”,
“TOP”:     “movie/top_rated”,
“POPULAR”: “movie/popular”,
}
movies = await fetch_movies(endpoint=endpoint_map.get(source, “trending/movie/week”))

```
sent = 0
for movie in movies:
    if sent >= limit:
        break
    data = await enrich_with_claude(movie)
    if data:
        ok = await send_movie_to_group(data, source)
        if ok:
            sent += 1
    await asyncio.sleep(2)  # Flood limit

logger.info(f"📊 Jami {sent}/{limit} kino yuborildi ({source})")
return sent
```

if **name** == “**main**”:
asyncio.run(discover_and_post(limit=3, source=“TREND”))`;

const parserCode = `# bot_parser.py

# Mavjud kino_bot.py ga import qilib qo’shing:

# from bot_parser import register_auto_movie_handler

import re, logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import MessageHandler, filters, ContextTypes, CallbackQueryHandler
from db_helper import add_movie_metadata, movie_exists_by_tmdb, get_pending_movies
from database import get_db  # Mavjud DB ulanishingiz

logger = logging.getLogger(**name**)

# ─────────────────────────────────────────

# Xabar parse qilish

# ─────────────────────────────────────────

def parse_auto_movie(text: str) -> dict | None:
def get(pattern, default=””):
m = re.search(pattern, text, re.MULTILINE)
return m.group(1).strip() if m else default

```
if "#AUTO_MOVIE" not in text:
    return None

try:
    return {
        "title":       get(r"📌 Nomi: (.+)"),
        "original":    get(r"🌐 Original: (.+)"),
        "genre":       get(r"🎭 Janr: (.+)"),
        "quality":     get(r"📺 Sifat: (.+)", "HD"),
        "language":    get(r"🌍 Til: (.+)", "Uzbek"),
        "rating":      float(get(r"⭐ Reyting: ([\d.]+)", "0")),
        "year":        get(r"📅 Yil: (.+)"),
        "description": get(r"📝 Tavsif: (.+)"),
        "poster_url":  get(r"🖼 Poster: (https?://\S+)"),
        "tmdb_id":     int(get(r"🔑 TMDB: (\d+)", "0")),
        "file_id":     None,   # Admin video qo'shganda to'ldiriladi
        "status":      "pending",
    }
except (ValueError, Exception) as e:
    logger.error(f"Parse xato: {e}")
    return None
```

# ─────────────────────────────────────────

# Guruh xabarini ushlash

# ─────────────────────────────────────────

async def handle_auto_movie(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
msg = update.message
if not msg or not msg.text:
return

```
data = parse_auto_movie(msg.text)
if not data:
    return

# Takrorlanishni tekshirish
if await movie_exists_by_tmdb(data["tmdb_id"]):
    await msg.reply_text(f"⚠️ {data['title']} allaqachon mavjud! (TMDB: {data['tmdb_id']})")
    return

# Pending holatda saqlash
movie_id = await add_movie_metadata(data)

# Admin uchun tugmalar
keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Videoni qo'sh", callback_data=f"addvideo_{movie_id}"),
     InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{movie_id}")]
])

await msg.reply_text(
    f"🆕 Yangi kino qo'shildi (pending):\n"
    f"🎬 {data['title']} ({data['year']})\n"
    f"🆔 DB ID: {movie_id}\n"
    f"📺 Video: Kutilmoqda...",
    reply_markup=keyboard
)
```

# ─────────────────────────────────────────

# Admin: Video qo’shish /add_video [id]

# ─────────────────────────────────────────

async def add_video_to_pending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
“”“Admin reply qiladi yoki /add_video 42 formatida”””
msg = update.message

```
# Buyruqdan ID olish
if ctx.args:
    movie_id = int(ctx.args[0])
elif msg.reply_to_message:
    # reply_to xabardan ID ni olish
    match = re.search(r"DB ID: (\d+)", msg.reply_to_message.text or "")
    movie_id = int(match.group(1)) if match else None
else:
    await msg.reply_text("❌ Foydalanish: /add_video [ID] yoki pending xabarini reply qiling")
    return

if not msg.video:
    await msg.reply_text("❌ Video yuboring!")
    return

file_id = msg.video.file_id

db = get_db()
await db.execute(
    "UPDATE movies SET file_id = ?, status = 'active' WHERE id = ?",
    (file_id, movie_id)
)
await db.commit()

await msg.reply_text(f"✅ Kino #{movie_id} uchun video qo'shildi va faollashtirildi!")
```

# ─────────────────────────────────────────

# Handler’larni ro’yxatga olish

# ─────────────────────────────────────────

def register_auto_movie_handler(app):
“”“application.py yoki bot.py da chaqiring”””
from telegram.ext import CommandHandler

```
# Guruh xabarlarini kuzatish
app.add_handler(MessageHandler(
    filters.TEXT & filters.Chat(chat_id=int(os.getenv("AUTO_GROUP_ID"))),
    handle_auto_movie
))
# Admin video qo'shish buyrug'i
app.add_handler(CommandHandler("add_video", add_video_to_pending))

logger.info("✅ Auto movie handler ro'yxatga olindi")`;
```

const dbHelperCode = `# db_helper.py

# Mavjud database.py ga qo’shimcha funksiyalar

import sqlite3, random, string
from database import get_db  # Sizning mavjud DB ulanish funksiyangiz

# ─────────────────────────────────────────

# Kino kodi generatsiya

# ─────────────────────────────────────────

def generate_code(length=6) -> str:
chars = string.ascii_uppercase + string.digits
return ‘’.join(random.choices(chars, k=length))

async def unique_code() -> str:
db = get_db()
while True:
code = generate_code()
exists = await db.fetchone(“SELECT id FROM movies WHERE code = ?”, (code,))
if not exists:
return code

# ─────────────────────────────────────────

# TMDB ID bo’yicha takrorlanish tekshirish

# ─────────────────────────────────────────

async def movie_exists_by_tmdb(tmdb_id: int) -> bool:
if not tmdb_id:
return False
db = get_db()
row = await db.fetchone(“SELECT id FROM movies WHERE tmdb_id = ?”, (tmdb_id,))
return row is not None

# ─────────────────────────────────────────

# Metadata saqlash (video yo’q, pending)

# ─────────────────────────────────────────

async def add_movie_metadata(data: dict) -> int:
db = get_db()
code = await unique_code()

```
# Sizning mavjud movies jadvalingizga moslashtiring
cursor = await db.execute("""
    INSERT INTO movies 
        (name, original_name, genre, quality, language, 
         rating, year, description, poster_url, 
         tmdb_id, code, file_id, status, added_by)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", (
    data["title"],
    data.get("original", data["title"]),
    data["genre"],
    data.get("quality", "HD"),
    data.get("language", "Uzbek"),
    data["rating"],
    data["year"],
    data["description"],
    data.get("poster_url", ""),
    data.get("tmdb_id", 0),
    code,
    data.get("file_id"),     # Hozircha None
    data.get("status", "pending"),
    "AI_AGENT"
))
await db.commit()

movie_id = cursor.lastrowid
return movie_id
```

# ─────────────────────────────────────────

# Pending kinolar ro’yxati

# ─────────────────────────────────────────

async def get_pending_movies() -> list:
db = get_db()
rows = await db.fetchall(
“SELECT id, name, year, code FROM movies WHERE status = ‘pending’ ORDER BY id DESC”
)
return rows

# ─────────────────────────────────────────

# SQLite’ga tmdb_id ustun qo’shish (bir marta)

# ─────────────────────────────────────────

def migrate_add_tmdb_column():
“”“Birinchi ishga tushirishda chaqiring”””
conn = sqlite3.connect(“kino_bot.db”)  # DB nomingiz
cur = conn.cursor()
try:
cur.execute(“ALTER TABLE movies ADD COLUMN tmdb_id INTEGER DEFAULT 0”)
cur.execute(“ALTER TABLE movies ADD COLUMN status TEXT DEFAULT ‘active’”)
cur.execute(“ALTER TABLE movies ADD COLUMN poster_url TEXT DEFAULT ‘’”)
cur.execute(“ALTER TABLE movies ADD COLUMN original_name TEXT DEFAULT ‘’”)
cur.execute(“ALTER TABLE movies ADD COLUMN added_by TEXT DEFAULT ‘ADMIN’”)
conn.commit()
print(“✅ Migratsiya muvaffaqiyatli!”)
except sqlite3.OperationalError as e:
print(f”ℹ️ Ustun allaqachon mavjud: {e}”)
finally:
conn.close()

if **name** == “**main**”:
migrate_add_tmdb_column()`;

const schedulerCode = `# scheduler.py — Termux uchun optimallashtirilgan

# pip install apscheduler

import asyncio, logging, os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ai_agent import discover_and_post
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format=”%(asctime)s — %(levelname)s — %(message)s”)

scheduler = AsyncIOScheduler(timezone=“Asia/Tashkent”)

def setup_jobs():
# Har kuni 09:00 — 5 ta trend kino
scheduler.add_job(
lambda: asyncio.create_task(discover_and_post(limit=5, source=“TREND”)),
CronTrigger(hour=9, minute=0),
id=“morning_trend”,
replace_existing=True
)
# Har kuni 18:00 — 3 ta top rated
scheduler.add_job(
lambda: asyncio.create_task(discover_and_post(limit=3, source=“TOP”)),
CronTrigger(hour=18, minute=0),
id=“evening_top”,
replace_existing=True
)
# Juma 20:00 — 10 ta haftalik trend
scheduler.add_job(
lambda: asyncio.create_task(discover_and_post(limit=10, source=“TREND”)),
CronTrigger(day_of_week=“fri”, hour=20, minute=0),
id=“weekly_big”,
replace_existing=True
)

async def main():
setup_jobs()
scheduler.start()

```
print("⏰ Scheduler faol (Toshkent vaqti)")
print("📅 09:00 — 5 ta trend kino")
print("📅 18:00 — 3 ta top kino")
print("📅 Juma 20:00 — 10 ta haftalik")
print("Ctrl+C — to'xtatish\\n")

try:
    while True:
        await asyncio.sleep(60)
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
    print("⛔ Scheduler to'xtatildi")
```

if **name** == “**main**”:
asyncio.run(main())

# ─────────────────────────────────────────

# Termux da fon rejimda ishlatish:

# ─────────────────────────────────────────

# nohup python scheduler.py > scheduler.log 2>&1 &

# 

# Yoki tmux bilan:

# tmux new -s scheduler

# python scheduler.py

# Ctrl+B, D  (fonga o’tish)`;

const codeMap = {
“ai_agent.py”: agentCode,
“bot_parser.py”: parserCode,
“db_helper.py”: dbHelperCode,
“scheduler.py”: schedulerCode,
};

const envVars = [
[“BOT_TOKEN”, “Asosiy Kino Bot tokeni”],
[“AGENT_BOT_TOKEN”, “AI Agent bot tokeni (alohida bot)”],
[“ANTHROPIC_API_KEY”, “Claude API kaliti”],
[“TMDB_API_KEY”, “TMDB API kaliti (bepul)”],
[“AUTO_GROUP_ID”, “Maxfiy guruh ID (masalan: -1001234567890)”],
[“ADMIN_IDS”, “Admin ID lari vergul bilan”],
];

export default function App() {
const [tab, setTab] = useState(“Integratsiya Rejasi”);

return (
<div style={{ fontFamily: “monospace”, background: “#0f172a”, minHeight: “100vh”, color: “#e2e8f0”, padding: 16 }}>
<div style={{ textAlign: “center”, marginBottom: 20 }}>
<div style={{ fontSize: 24 }}>🔗 Kino Bot v1.2.9 × AI Agent</div>
<div style={{ color: “#94a3b8”, fontSize: 12, marginTop: 4 }}>python-telegram-bot 20.7 • SQLite • Claude API • TMDB</div>
</div>

```
  {/* Tabs */}
  <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
    {tabs.map(t => (
      <button key={t} onClick={() => setTab(t)} style={{
        padding: "7px 14px", borderRadius: 8, border: "none", cursor: "pointer",
        background: tab === t ? "#6366f1" : "#1e293b",
        color: tab === t ? "#fff" : "#94a3b8", fontSize: 12, fontFamily: "monospace"
      }}>{t}</button>
    ))}
  </div>

  {/* Plan tab */}
  {tab === "Integratsiya Rejasi" && (
    <div>
      {/* Flow steps */}
      {plan.map((p, i) => (
        <div key={i} style={{ display: "flex", gap: 12, marginBottom: 12, alignItems: "flex-start" }}>
          <div style={{
            background: p.color, borderRadius: "50%", width: 30, height: 30,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontWeight: "bold", fontSize: 14, flexShrink: 0, marginTop: 2
          }}>{p.step}</div>
          <div style={{ background: "#1e293b", borderRadius: 10, padding: 12, flex: 1 }}>
            <div style={{ color: p.color, fontSize: 13, fontWeight: "bold" }}>{p.title}</div>
            <div style={{ color: "#cbd5e1", fontSize: 12, marginTop: 4 }}>{p.desc}</div>
            <div style={{ color: "#64748b", fontSize: 11, marginTop: 6 }}>{p.note}</div>
          </div>
        </div>
      ))}

      {/* File structure */}
      <div style={{ background: "#1e293b", borderRadius: 10, padding: 14, marginTop: 8 }}>
        <div style={{ color: "#6366f1", fontSize: 12, marginBottom: 10 }}>📁 FAYL TUZILISHI</div>
        <pre style={{ color: "#22c55e", fontSize: 11, margin: 0, lineHeight: 1.8 }}>{`kino_bot/
```

├── kino_bot.py          ← Asosiy bot (mavjud)
├── database.py          ← DB ulanish (mavjud)
├── ai_agent.py          ← 🆕 AI movie discovery
├── bot_parser.py        ← 🆕 Auto-add handler
├── db_helper.py         ← 🆕 Qo’shimcha DB funksiyalar
├── scheduler.py         ← 🆕 Avtomatik ishga tushirish
└── .env                 ← 🔑 API kalitlar`}</pre>
</div>

```
      {/* .env */}
      <div style={{ background: "#1e293b", borderRadius: 10, padding: 14, marginTop: 12 }}>
        <div style={{ color: "#f59e0b", fontSize: 12, marginBottom: 10 }}>🔑 .ENV FAYLIGA QO'SHING</div>
        {envVars.map(([k, v]) => (
          <div key={k} style={{ display: "flex", gap: 10, marginBottom: 6, alignItems: "center" }}>
            <span style={{ color: "#f59e0b", minWidth: 160, fontSize: 11 }}>{k}=</span>
            <span style={{ color: "#64748b", fontSize: 11 }}>#{v}</span>
          </div>
        ))}
      </div>

      {/* kino_bot.py ga qo'shish */}
      <div style={{ background: "#1e293b", borderRadius: 10, padding: 14, marginTop: 12 }}>
        <div style={{ color: "#10b981", fontSize: 12, marginBottom: 10 }}>⚙️ kino_bot.py GA QO'SHISH (oxiriga)</div>
        <pre style={{ color: "#22c55e", fontSize: 11, margin: 0 }}>{`# kino_bot.py — mavjud "def main():" funksiyasiga qo'shing
```

from bot_parser import register_auto_movie_handler

def main():
app = ApplicationBuilder().token(BOT_TOKEN).build()

```
# ... mavjud handlerlar ...

# AI auto-add handleri (qo'shing)
register_auto_movie_handler(app)

app.run_polling()`}</pre>
      </div>

      {/* Install */}
      <div style={{ background: "#1e293b", borderRadius: 10, padding: 14, marginTop: 12 }}>
        <div style={{ color: "#0ea5e9", fontSize: 12, marginBottom: 10 }}>📦 O'RNATISH</div>
        <pre style={{ color: "#22c55e", fontSize: 11, margin: 0 }}>{`# Termux:
```

pip install anthropic httpx apscheduler python-dotenv

# Migratsiya (bir marta):

python db_helper.py

# Test:

python ai_agent.py

# Fon rejim:

nohup python scheduler.py > scheduler.log 2>&1 &`}</pre>
</div>
</div>
)}

```
  {/* Code tabs */}
  {tab !== "Integratsiya Rejasi" && (
    <div style={{ background: "#1e293b", borderRadius: 10, padding: 16 }}>
      <pre style={{ color: "#22c55e", fontSize: 11, margin: 0, overflowX: "auto", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
        {codeMap[tab]}
      </pre>
    </div>
  )}
</div>
```

);
}