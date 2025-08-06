import aiosqlite
from config import DATABASE_FILE, MAIN_ADMIN, DEFAULT_SETTINGS

class Database:
    def __init__(self):
        self.db_file = DATABASE_FILE

    async def create_tables(self):
        async with aiosqlite.connect(self.db_file) as db:
            # Foydalanuvchilar jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    fullname TEXT,
                    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Kinolar jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS movies (
                    code INTEGER PRIMARY KEY,
                    title TEXT,
                    format TEXT,
                    language TEXT,
                    file_id TEXT,
                    views INTEGER DEFAULT 0,
                    is_deleted INTEGER DEFAULT 0
                )
            ''')
            
            # Kanallar jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    username TEXT PRIMARY KEY
                )
            ''')
            
            # Reklamalar jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS ads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_file_id TEXT,
                    text TEXT,
                    button_text TEXT,
                    button_url TEXT,
                    schedule_time TEXT,
                    repeat_count INTEGER
                )
            ''')
            
            # Adminlar jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY
                )
            ''')
            
            # Sozlamalar jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            await db.commit()

    # Foydalanuvchi qo'shish
    async def add_user(self, user_id: int, username: str, fullname: str):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute(
                'INSERT OR IGNORE INTO users (id, username, fullname) VALUES (?, ?, ?)',
                (user_id, username, fullname)
            )
            await db.commit()

    # Kino qo'shish
    async def add_movie(self, title: str, format: str, language: str, file_id: str) -> int:
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute('SELECT MAX(code) FROM movies')
            result = await cursor.fetchone()
            next_code = (result[0] or 0) + 1
            
            await db.execute(
                'INSERT INTO movies (code, title, format, language, file_id) VALUES (?, ?, ?, ?, ?)',
                (next_code, title, format, language, file_id)
            )
            await db.commit()
            return next_code

    # Kino o'chirish
    async def delete_movie(self, code: int):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('UPDATE movies SET is_deleted = 1 WHERE code = ?', (code,))
            await db.commit()

    # Ko'rishlar sonini oshirish
    async def increment_views(self, code: int):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('UPDATE movies SET views = views + 1 WHERE code = ?', (code,))
            await db.commit()

    # Kino ma'lumotlarini olish
    async def get_movie(self, code: int):
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute(
                'SELECT * FROM movies WHERE code = ? AND is_deleted = 0',
                (code,)
            )
            return await cursor.fetchone()

    # Adminlar ro'yxatini olish
    async def get_admins(self) -> list:
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute('SELECT user_id FROM admins')
            return [row[0] for row in await cursor.fetchall()]

    # Admin qo'shish
    async def add_admin(self, user_id: int):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (user_id,))
            await db.commit()

    # Adminni o'chirish
    async def remove_admin(self, user_id: int):
        if user_id != MAIN_ADMIN:
            async with aiosqlite.connect(self.db_file) as db:
                await db.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
                await db.commit()

    # Kanal qo'shish
    async def add_channel(self, username: str):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('INSERT OR REPLACE INTO channels (username) VALUES (?)', (username,))
            await db.commit()

    # Kanalni o'chirish
    async def remove_channel(self, username: str):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('DELETE FROM channels WHERE username = ?', (username,))
            await db.commit()

    # Kanallar ro'yxatini olish
    async def get_channels(self):
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute('SELECT username FROM channels')
            return [row[0] for row in await cursor.fetchall()]

    # Reklama qo'shish
    async def add_ad(self, image_file_id: str, text: str, button_text: str, button_url: str, schedule_time: str, repeat_count: int):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('''
                INSERT INTO ads (image_file_id, text, button_text, button_url, schedule_time, repeat_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (image_file_id, text, button_text, button_url, schedule_time, repeat_count))
            await db.commit()

    # Reklamani o'chirish
    async def delete_ad(self, ad_id: int):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('DELETE FROM ads WHERE id = ?', (ad_id,))
            await db.commit()

    # Rejalashtirilgan reklamalarni olish
    async def get_scheduled_ads(self):
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute('SELECT * FROM ads WHERE repeat_count > 0')
            return await cursor.fetchall()

    # Reklama takrorlanishlarini yangilash
    async def update_ad_count(self, ad_id: int, new_count: int):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('UPDATE ads SET repeat_count = ? WHERE id = ?', (new_count, ad_id))
            await db.commit()

    # Statistika olish
    async def get_stats(self) -> dict:
        async with aiosqlite.connect(self.db_file) as db:
            stats = {}
            
            cursor = await db.execute('SELECT COUNT(*) FROM users')
            stats['users'] = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT COUNT(*) FROM movies WHERE is_deleted = 0')
            stats['movies'] = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT SUM(views) FROM movies')
            stats['total_views'] = (await cursor.fetchone())[0] or 0
            
            return stats

    # Sozlamalarni olish
    async def get_setting(self, key: str) -> str:
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute('SELECT value FROM settings WHERE key = ?', (key,))
            result = await cursor.fetchone()
            return result[0] if result else DEFAULT_SETTINGS.get(key)

    # Sozlamani o'zgartirish
    async def set_setting(self, key: str, value: str):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
            await db.commit()

    # Foydalanuvchilar ro'yxatini olish
    async def get_all_users(self) -> list:
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute('SELECT id FROM users')
            return [row[0] for row in await cursor.fetchall()]
