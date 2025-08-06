from dotenv import load_dotenv
import os

# .env faylidan o'zgaruvchilarni yuklash
load_dotenv()

# Bot token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Asosiy admin ID
MAIN_ADMIN = int(os.getenv('MAIN_ADMIN', 6887251996))

# Ma'lumotlar bazasi fayli
DATABASE_FILE = "movies.db"

# Bot sozlamalari
DEFAULT_SETTINGS = {
    "force_subscribe": "true",
    "notification_new_user": "true"
}
