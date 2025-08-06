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

    # Reklama qo'shish
    async def add_ad(self, image_file_id: str, text: str, button_text: str, button_url: str, schedule_time: str, repeat_count: int):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('''
                INSERT INTO ads (image_file_id, text, button_text, button_url, schedule_time, repeat_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (image_file_id, text, button_text, button_url, schedule_time, repeat_count))
            await db.commit()

    # Reklama o'chirish
    async def delete_ad(self, ad_id: int):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('DELETE FROM ads WHERE id = ?', (ad_id,))
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
