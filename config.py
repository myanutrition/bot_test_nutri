# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота — берётся из .env файла на сервере
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Канал для проверки подписки
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@myanutrition")

# ID администраторов (через запятую)
ADMIN_IDS = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]

# Ссылки
GROUP_URL = "https://myanutrition.ru/group"
PODCAST_URL = "https://podcast.ru/1742928597"

# Фото для приветственного сообщения (необязательно)
START_PHOTO_FILE_ID = os.getenv("START_PHOTO_FILE_ID", "").strip()
START_PHOTO_PATH = os.getenv("START_PHOTO_PATH", "start_photo.jpg")

# База данных
DB_PATH = os.getenv("DB_PATH", "stats.db")
