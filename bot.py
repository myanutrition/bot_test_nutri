import logging
import sqlite3
import os
from datetime import datetime, timedelta
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@myanutrition"
SEND_HOUR = 7
SEND_MINUTE = 0
ADMIN_CHAT_ID = 7917196527  # твой личный chat_id для уведомлений

# ==================== FILE IDs ====================
VIDEO_NOTE_WELCOME = "DQACAgIAAxkBAAMmaivD3RNQAAGqPsePgjt-3pvjfu8kAAJRlQACsWNgSaHwSjhTtWBXPAQ"
VIDEO_NOTE_FINAL = "DQACAgIAAxkDAAMjaiu4TIfoRkGRS7rqDomugaOruV8AAnuUAAKxY2BJx2IupzoJWSE8BA"
PHOTO_DAY9 = "AgACAgIAAxkBAAINKGo66DdkVNMAacFvAYACiHBzoJXk6gACOyBrG6ac2ElCweKxRRTS4gEAAwIAA3gAazwE"

AUDIOS = {
    0: "CQACAgIAAxkBAAMtaivFmYh_fIFsGFMezWmgRkpeqfcAApGjAAL3PFlJwIYOskcZXrU8BA",
    1: "CQACAgIAAxkBAAMqaivFmaH-iuRPMJIwx4MyNn3zBLkAAo2jAAL3PFlJGEpDBNWw2ow8BA",
    2: "CQACAgIAAxkBAAMvaivFmaVxoY7UhPrYL22OwYem6O0AApmjAAL3PFlJjCuuH0oNumg8BA",
    3: "CQACAgIAAxkBAAMsaivFmcv6jylMlr5rPep_DV_8iyoAApCjAAL3PFlJzVNrPNgIYz08BA",
    4: "CQACAgIAAxkBAAMxaivFmRw0HhdYgVzaNyiR6k2jXNEAAp6jAAL3PFlJuiP-Rfb6xbs8BA",
    5: "CQACAgIAAxkBAAMwaivFmbBmswI6C2V34Rv9KBDsYQEAApujAAL3PFlJE513kMpSh808BA",
    6: "CQACAgIAAxkBAAMuaivFmUciTFFFBDBSrQLyZDd6DrMAApWjAAL3PFlJK8hUVqleKys8BA",
    7: "CQACAgIAAxkBAAMraivFmRxDuGBF6rh7-JO_ApuMyQIAAo-jAAL3PFlJ-dXUDizbJWQ8BA",
}

# ==================== ТЕКСТЫ ====================

TEXT_NOT_SUBSCRIBED = "Чтобы получить доступ к аудиосерии, подпишись на канал автора 🎙️"

TEXT_START_1 = (
    "Привет! 👋 Я Юля Минченко, нутрициолог с высшим образованием и сертифицированный коуч по питанию 🌿\n\n"
    "Это аудиосерия «Знаю, но не делаю» 🎧\n\n"
    "Вас ждёт 7 коротких аудио о том, почему разобраться с питанием не получается, даже если вы уже много знаете. "
    "Эта серия основана на опыте работы с сотнями клиентов, которые столкнулись с этой проблемой."
)

TEXT_START_2 = (
    "Мы не будем говорить про меню, марафоны, подсчёт калорий, запрет сладкого и волшебные биодобавки 🚫\n\n"
    "Вы узнаете про причины, которые влияют на питание в реальной жизни: еду вокруг нас, прошлый диетный опыт, эмоции и привычные сценарии 💡"
)

TEXT_START_3 = (
    "Каждый день я буду присылать одно аудио и небольшое задание для наблюдения за собой 📝 "
    "Слушайте в комфортном темпе и отмечайте, что из этого похоже на вашу ситуацию.\n\n"
    "Начинаем с первой причины! ▶️"
)

TEXTS_BEFORE = {
    1: (
        "🏠 *День 1. Окружающая среда*\n\n"
        "Сегодня говорим про окружающую среду. Это всё, что находится вокруг нас и влияет на выбор еды: "
        "дом, работа, семья, родственники, гости, магазины, доставка, привычки близких людей.\n\n"
        "Питание зависит не только от знаний 💡 На него сильно влияет то, что лежит на виду, что удобно взять, "
        "что предлагают рядом и какой выбор доступен в течение дня.\n\n"
        "В первом аудио говорим о том, почему лучше изменить то, что рядом, чем ограничить себя силой воли 💪"
    ),
    2: (
        "🍟 *День 2. Гипервкусная еда и маркетинг*\n\n"
        "Ммм, эти чипсы! А вот и пачка исчезла — как тут остановиться? 😅\n\n"
        "Сегодня говорим про еду, с которой сложно остановиться. Это не только сладкое. Это ещё и фастфуд, закуски — "
        "всё, где много вкуса, запаха, текстуры, соли, сахара, жира, хруста, соусов. Рядом с ними возникает ощущение, "
        "что хочется продолжать ещё и ещё.\n\n"
        "Такая еда хорошо продаётся, красиво выглядит, быстродоступна и не требует усилий 🛒\n\n"
        "Во втором аудио говорим о том, почему желание съесть ещё не говорит о вашей слабости, "
        "и почему дело не только в дисциплине 💡"
    ),
    3: (
        "🖤🤍 *День 3. Чёрно-белое мышление*\n\n"
        "Сегодня говорим про мышление, когда питание делится на идеальное и ужасное. "
        "Съели сладкое — и дальше день будто уже зачёркнут: несите мне всё мороженое! 🍦 Сгорел сарай, гори и хата!\n\n"
        "Такой подход мешает питанию быть нормальной и естественной частью жизни. "
        "Еда превращается в постоянную оценку себя, а любое отклонение воспринимается как личный провал 😔\n\n"
        "В третьем аудио говорим о том, почему так важно бороться с чёрно-белым мышлением в питании 💡"
    ),
    4: (
        "🔍 *День 4. Самообман*\n\n"
        "Сегодня говорим про самообман. Мы не будем обвинять себя, а научимся с открытыми глазами "
        "посмотреть на то, что происходит с питанием 👀\n\n"
        "Мы можем думать, что едим мало, что нам мешает только нехватка времени, что питание в целом нормальное, "
        "что проблема только в сладком или что перееданий нет, а есть любовь к вкусной еде. "
        "Такие объяснения могут закрывать настоящую причину.\n\n"
        "В четвёртом аудио говорим о том, как увидеть разницу между тем, что мы думаем о своём питании, "
        "и тем, что происходит на самом деле 💡"
    ),
    5: (
        "📋 *День 5. Диетный опыт*\n\n"
        "Сегодня говорим про диетный опыт. Если в прошлом у вас было много попыток худеть, считать калории, "
        "запрещать продукты, терпеть, срываться и начинать заново — это влияет на отношения с едой 💔\n\n"
        "После такого опыта еда перестаёт быть обычной частью жизни. Тема веса и тела тесно связывается с виной, "
        "страхом, желанием всё контролировать. Возникает недоверие к себе и ощущение, что постоянно нужно брать себя в руки.\n\n"
        "В пятом аудио говорим о том, как прошлые диеты могут мешать сейчас, даже если вы уже не сидите на диете 💡"
    ),
    6: (
        "💭 *День 6. Вторичная выгода*\n\n"
        "Сегодня говорим про вторичную выгоду. Дело в том, что еда может выполнять для вас важную функцию.\n\n"
        "Она может помогать отдыхать, переключаться, получать удовольствие, выдерживать усталость, "
        "справляться с тревогой, злостью, напряжением или одиночеством 🤍 Тогда ваше питание не меняется "
        "не из-за вашего нежелания измениться, а потому что еда закрывает какую-то потребность.\n\n"
        "В шестом аудио говорим о том, какую роль еда может играть в жизни и почему сначала важно понять "
        "эту роль, а уже потом пытаться что-то менять 💡"
    ),
    7: (
        "💛 *День 7. Эмоции*\n\n"
        "Сегодня финальное аудио. Говорим про эмоциональное переедание — самую главную проблему, "
        "с которой ко мне приходят клиенты.\n\n"
        "Еда является быстрым способом справиться с эмоциями 😔 Стресс, усталость, тревога, злость, скука, "
        "одиночество, напряжение, обида — всё это может вести нас к гипервкусной и калорийной еде, "
        "особенно если сложно понять, что именно я чувствую и что мне сейчас нужно.\n\n"
        "В седьмом аудио говорим о том, какие эмоции чаще всего заедают и почему совет «просто перестать заедать» не помогает 💡"
    ),
}

TEXTS_AFTER = {
    1: "🎧 После аудио понаблюдайте, что в вашей окружающей среде помогает качественному питанию, а что уводит в сторону.",
    2: "🎧 После аудио понаблюдайте, на каких продуктах вам сложнее остановиться и в какой момент дня это происходит.",
    3: "🎧 После аудио попробуйте заметить, в каких ситуациях у вас возникает мысль, что раз не получилось идеально — можно уже не продолжать.",
    4: "🎧 После аудио спросите себя, где вы можете не до конца видеть реальную картину своего питания.",
    5: (
        "🎧 После аудио подумайте, какие правила из прошлого до сих пор влияют на ваше питание.\n\n"
        "Узнать подробнее про групповое сопровождение можно по ссылке 👇"
    ),
    6: (
        "🎧 После аудио подумайте, что вы получаете через еду, кроме вкуса и насыщения.\n\n"
        "В сопровождении мы работаем не только с едой, но и с истинными причинами перееданий 🌿"
    ),
    7: (
        "🎧 Если в этой серии вы узнали себя и готовы изменить ситуацию — приглашаю вас в групповое сопровождение!\n\n"
        "Существуют конкретные навыки в питании, которые помогают худеть без диет и навсегда 🌿 "
        "Вы сможете не только о них узнать, но и освоить — шаг за шагом. Результат не заставит себя долго ждать!\n\n"
        "В группе будет 6 мест — так у меня есть возможность видеть участников и давать обратную связь "
        "каждому лично. Кстати, в формате таких же аудио, но именно про Вас! 🎙️"
    ),
}

TEXT_FINAL_1 = (
    "Спасибо, что прошли эту аудиосерию 🙏\n\n"
    "Я хотела сделать её не про «правильное питание», а про то, почему это «правильное питание» не получается встроить в жизнь.\n\n"
    "Помните 💡\n\n"
    "Дело не в знаниях. Дело в усталости от попыток, старом опыте, окружающей среде, эмоциях, "
    "запретах и привычных сценариях, которые копились вокруг еды годами.\n\n"
    "Чтобы мы не потерялись, оставляю ссылки 👇"
)

TEXT_FINAL_2 = (
    "Выберите одну мысль из этой серии — например, про работу с эмоциями — и наблюдайте за собой в ближайшие дни. "
    "Будьте любознательными, добрыми и честными с собой 🤍\n\n"
    "До скорой встречи, ваша Юля! 👋"
)

TEXT_FINAL_3 = "Напишите, пожалуйста, в этот бот, какая мысль из аудиосерии вам особенно понравилась 💬"

TEXT_DAY8 = (
    "📚 Бонус. Материалы для углубления\n\n"
    "Вы прошли все 7 аудио — это здорово!\n\n"
    "Хочу поделиться несколькими постами из моего канала, которые хорошо дополняют то, о чём мы говорили в серии. Почитайте в удобное время 👇\n\n"
    "• <a href=\"https://t.me/myanutrition/2052\">Что влияет на нас, когда мы переедаем</a>\n"
    "• <a href=\"https://t.me/myanutrition/2087\">У меня плохая генетика, поэтому я набираю вес</a>\n"
    "• <a href=\"https://t.me/myanutrition/2118\">СРЫВ — не используйте это слово</a>\n"
    "• <a href=\"https://t.me/myanutrition/2106\">Откаты в питании — это нормально?! Диетная карусель</a>"
)

TEXT_DAY9 = (
    "Пока мой голос звучал в твоих наушниках, ты могла заметить важную вещь. Сложные отношения с едой — не от незнания и не потому, что ты слабовольная 🤍\n\n"
    "Скорее всего, ты и так прекрасно понимаешь, что надо есть регулярнее, добавлять белок, овощи, не доводить себя до дикого голода, не жить на кофе, кусочничестве и сладком до вечера.\n\n"
    "Но потом день идёт не по плану. Обед опять где-то между делами, сил к вечеру нет, сладкое становится самым быстрым способом себя поддержать, а потом думаешь: <i>«ну всё, завтра нормально начну»</i> 😔\n\n"
    "Так можно <b>годами</b> читать полезные материалы, сохранять рецепты, проходить тесты, слушать подкасты, понимать причины перееданий — и всё равно чувствовать, что тема еды занимает слишком много места в голове.\n\n"
    "Я очень хорошо понимаю, как это <b>выматывает</b> 💛\n\n"
    "В групповом сопровождении мы будем работать не только с продуктами, которые ты ешь. В первую очередь мы разберёмся с тем, что стоит за этим: пропусками еды, усталостью, эмоциональным голодом, перекусами на бегу, сладким без чувства вины, насыщением, тревогой из-за веса и привычкой вспоминать о себе только тогда, когда сил уже нет.\n\n"
    "🗓 <b>6 июля открываются продажи</b> в моё групповое сопровождение.\n\n"
    "Это формат для тех, кто <b>устал каждый раз начинать заново</b> и хочет наконец выстроить питание спокойно — с поддержкой, понятной системой и маленькими шагами, которые правда получается делать 🌿\n\n"
    "✨ Для участниц <b>первого дня продаж</b> будет бонус — индивидуальная консультация с разбором питания, которую можно использовать в течение года.\n\n"
    "Если ты узнала себя в аудио, я очень хочу поработать с тобой лично 💛\n\n"
    "<b>Старт продаж — 6 июля.</b>\n"
    "В группе будет всего <b>6 мест.</b>\n"
    "Запишись в лист ожидания, чтобы не пропустить подробности 👇"
)

# ==================== КНОПКИ ====================

def kb_subscribe():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Подписаться на канал", url="https://t.me/myanutrition")],
        [InlineKeyboardButton("✅ Я подписался(ась)", callback_data="check_sub")],
    ])

def kb_interesting():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Интересно! 🌟", callback_data="btn_interesting")],
    ])

def kb_lets_go():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Отлично, давай начнём! ▶️", callback_data="btn_lets_go")],
    ])

def kb_day5():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Подробнее о группе", callback_data="btn_group_d5")],
    ])

def kb_day6():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Лист ожидания", callback_data="btn_waitlist_d6")],
    ])

def kb_day7():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Лист ожидания", callback_data="btn_waitlist_d7")],
    ])

def kb_day9():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Вступить", callback_data="btn_waitlist_d9")],
    ])

def kb_final_1():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Telegram-канал", callback_data="btn_channel_final")],
        [InlineKeyboardButton("🎙️ Подкаст", callback_data="btn_podcast_final")],
        [InlineKeyboardButton("🌿 Групповое сопровождение", callback_data="btn_group_final")],
        [InlineKeyboardButton("📋 Лист ожидания", callback_data="btn_waitlist_final")],
    ])

def kb_final_3():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Написать", callback_data="btn_feedback")],
    ])

# URL для кнопок
BUTTON_URLS = {
    "btn_group_d5": "https://myanutrition.ru/group",
    "btn_waitlist_d6": "https://t.me/+jeRJ8g609qllZWQy",
    "btn_waitlist_d7": "https://t.me/+jeRJ8g609qllZWQy",
    "btn_waitlist_d9": "https://t.me/+jeRJ8g609qllZWQy",
    "btn_channel_final": "https://t.me/myanutrition",
    "btn_podcast_final": "https://podcast.ru/1742928597",
    "btn_group_final": "https://myanutrition.ru/group",
    "btn_waitlist_final": "https://t.me/+jeRJ8g609qllZWQy",
    "btn_feedback": "https://t.me/MyaNutrition_Bot",
}

BUTTON_NAMES = {
    "btn_group_d5": "Подробнее о группе",
    "btn_waitlist_d6": "📋 Лист ожидания",
    "btn_waitlist_d7": "📋 Лист ожидания",
    "btn_waitlist_d9": "📋 Вступить",
    "btn_channel_final": "💬 Telegram-канал",
    "btn_podcast_final": "🎙️ Подкаст",
    "btn_group_final": "🌿 Групповое сопровождение",
    "btn_waitlist_final": "📋 Лист ожидания",
    "btn_feedback": "✍️ Написать",
}

# ==================== БАЗА ДАННЫХ ====================

def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            start_date TEXT,
            last_day INTEGER DEFAULT 1,
            blocked INTEGER DEFAULT 0,
            subscribed INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT,
            user_id INTEGER,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS button_clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            button TEXT,
            user_id INTEGER,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id):
    """Регистрирует пользователя. start_date пока NULL — курс ещё не начался."""
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO users (user_id, start_date, last_day, subscribed) VALUES (?, ?, ?, ?)",
        (user_id, None, 0, 1)
    )
    c.execute(
        "INSERT INTO stats (event, user_id, created_at) VALUES (?, ?, ?)",
        ("new_user", user_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def set_course_started(user_id):
    """Записывает start_date и last_day=1 когда пользователь нажал 'Давай начнём!'"""
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    c.execute(
        "UPDATE users SET start_date = ?, last_day = 1 WHERE user_id = ?",
        (today, user_id)
    )
    conn.commit()
    conn.close()

def log_event(event, user_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO stats (event, user_id, created_at) VALUES (?, ?, ?)",
        (event, user_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def log_button_click(button, user_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO button_clicks (button, user_id, created_at) VALUES (?, ?, ?)",
        (button, user_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def mark_blocked(user_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET blocked = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    """Возвращает только тех кто уже нажал 'Давай начнём!' (start_date не NULL)"""
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT user_id, start_date, last_day FROM users WHERE blocked = 0 AND start_date IS NOT NULL")
    rows = c.fetchall()
    conn.close()
    return rows

def update_last_day(user_id, day):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET last_day = ? WHERE user_id = ?", (day, user_id))
    conn.commit()
    conn.close()

def user_exists(user_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_stats():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    # Всего пользователей
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]

    # Заблокировали бота
    c.execute("SELECT COUNT(*) FROM users WHERE blocked = 1")
    blocked = c.fetchone()[0]

    # Не подписались и ушли
    c.execute("SELECT COUNT(*) FROM stats WHERE event = 'not_subscribed'")
    not_subscribed = c.fetchone()[0]

    # Новые за неделю
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    c.execute("SELECT COUNT(*) FROM stats WHERE event = 'new_user' AND created_at >= ?", (week_ago,))
    new_week = c.fetchone()[0]

    # По дням
    days_stats = {}
    for day in range(1, 8):
        c.execute("SELECT COUNT(*) FROM users WHERE last_day = ? AND blocked = 0", (day,))
        days_stats[day] = c.fetchone()[0]

    # Завершили (дошли до дня 7)
    c.execute("SELECT COUNT(*) FROM users WHERE last_day = 7 AND blocked = 0")
    completed = c.fetchone()[0]

    # Клики по кнопкам
    c.execute("SELECT button, COUNT(*) FROM button_clicks GROUP BY button")
    clicks = dict(c.fetchall())

    conn.close()
    return {
        "total": total,
        "blocked": blocked,
        "not_subscribed": not_subscribed,
        "new_week": new_week,
        "days": days_stats,
        "completed": completed,
        "clicks": clicks,
    }

# ==================== ПРОВЕРКА ПОДПИСКИ ====================

async def is_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

# ==================== УВЕДОМЛЕНИЯ АДМИНУ ====================

async def notify_admin(bot, text):
    try:
        await bot.send_message(ADMIN_CHAT_ID, text)
    except Exception as e:
        logging.error(f"Ошибка уведомления админа: {e}")

# ==================== ОТПРАВКА КОНТЕНТА ====================

async def safe_send(bot, user_id, func, *args, **kwargs):
    for attempt in range(3):
        try:
            return await func(user_id, *args, **kwargs)
        except Exception as e:
            if "blocked" in str(e).lower() or "deactivated" in str(e).lower():
                mark_blocked(user_id)
                return None
            if attempt < 2:
                logging.warning(f"Попытка {attempt+1} не удалась для {user_id}: {e}. Повтор через 5 сек...")
                await asyncio.sleep(5)
            else:
                logging.error(f"Все 3 попытки не удались для {user_id}: {e}")
    return None

async def send_welcome(bot, user_id):
    # Сообщение 1
    await safe_send(bot, user_id, bot.send_message, TEXT_START_1)
    await asyncio.sleep(1)

    # Приветственный кружок
    await safe_send(bot, user_id, bot.send_video_note, VIDEO_NOTE_WELCOME)
    await asyncio.sleep(1)

    # Сообщение 2 + кнопка "Интересно!"
    await safe_send(bot, user_id, bot.send_message, TEXT_START_2, reply_markup=kb_interesting())


async def send_day0_and_day1_start(bot, user_id):
    # Аудио День 0
    await safe_send(bot, user_id, bot.send_audio, AUDIOS[0])
    await asyncio.sleep(1)

    # Сообщение 3 + кнопка "Отлично, давай начнём!"
    await safe_send(bot, user_id, bot.send_message, TEXT_START_3, reply_markup=kb_lets_go())


async def send_day1(bot, user_id):
    # День 1 текст до аудио
    await safe_send(bot, user_id, bot.send_message, TEXTS_BEFORE[1], parse_mode="Markdown")
    await asyncio.sleep(1)

    # Аудио День 1
    await safe_send(bot, user_id, bot.send_audio, AUDIOS[1])
    await asyncio.sleep(1)

    # Текст после аудио
    await safe_send(bot, user_id, bot.send_message, TEXTS_AFTER[1])


async def send_day(bot, user_id, day):
    if day > 9:
        return

    # Дни 8 и 9 — особая логика
    if day == 8:
        await safe_send(bot, user_id, bot.send_message, TEXT_DAY8, parse_mode="HTML")
        update_last_day(user_id, day)
        return

    if day == 9:
        await safe_send(bot, user_id, bot.send_photo, PHOTO_DAY9)
        await asyncio.sleep(1)
        await safe_send(bot, user_id, bot.send_message, TEXT_DAY9, parse_mode="HTML", reply_markup=kb_day9())
        update_last_day(user_id, day)
        return

    await safe_send(bot, user_id, bot.send_message, TEXTS_BEFORE[day], parse_mode="Markdown")
    await asyncio.sleep(1)

    await safe_send(bot, user_id, bot.send_audio, AUDIOS[day])
    await asyncio.sleep(1)

    keyboard = None
    if day == 5:
        keyboard = kb_day5()
    elif day == 6:
        keyboard = kb_day6()
    elif day == 7:
        keyboard = kb_day7()

    await safe_send(bot, user_id, bot.send_message, TEXTS_AFTER[day], reply_markup=keyboard)

    if day == 7:
        await asyncio.sleep(1)
        await safe_send(bot, user_id, bot.send_video_note, VIDEO_NOTE_FINAL)
        await asyncio.sleep(1)
        await safe_send(bot, user_id, bot.send_message, TEXT_FINAL_1, reply_markup=kb_final_1())
        await asyncio.sleep(1)
        await safe_send(bot, user_id, bot.send_message, TEXT_FINAL_2)
        await asyncio.sleep(1)
        await safe_send(bot, user_id, bot.send_message, TEXT_FINAL_3, reply_markup=kb_final_3())

    update_last_day(user_id, day)

# ==================== ЕЖЕДНЕВНАЯ ЗАДАЧА ====================

async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    users = get_all_users()
    today = datetime.now().date()

    for user_id, start_date_str, last_day in users:
        if not start_date_str:
            continue
        try:
            start_date = datetime.fromisoformat(start_date_str).date()
            days_passed = (today - start_date).days
            next_day = last_day + 1

            if next_day <= 9 and days_passed == (next_day - 1):
                await send_day(context.bot, user_id, next_day)
                await asyncio.sleep(2)
        except Exception as e:
            logging.error(f"Ошибка в daily_job для пользователя {user_id}: {e}")

# ==================== ХЭНДЛЕРЫ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_exists(user_id):
        await update.message.reply_text("Вы уже зарегистрированы! Ожидайте следующее аудио 🎧")
        return

    subscribed = await is_subscribed(context.bot, user_id)
    if not subscribed:
        log_event("not_subscribed", user_id)
        await update.message.reply_text(TEXT_NOT_SUBSCRIBED, reply_markup=kb_subscribe())
        return

    add_user(user_id)
    username = update.effective_user.username or update.effective_user.first_name
    await notify_admin(context.bot, f"🆕 Новый пользователь: @{username} (ID: {user_id})")
    await send_welcome(context.bot, user_id)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # Проверка подписки
    if data == "check_sub":
        subscribed = await is_subscribed(context.bot, user_id)
        if not subscribed:
            await query.message.reply_text(
                "Похоже, вы ещё не подписались 🙈 Подпишитесь на канал и нажмите кнопку снова!",
                reply_markup=kb_subscribe()
            )
            return
        if user_exists(user_id):
            await query.message.reply_text("Вы уже зарегистрированы! Ожидайте следующее аудио 🎧")
            return
        add_user(user_id)
        username = query.from_user.username or query.from_user.first_name
        await notify_admin(context.bot, f"🆕 Новый пользователь: @{username} (ID: {user_id})")
        await query.message.reply_text("Отлично, подписка подтверждена! 🎉 Начинаем!")
        await send_welcome(context.bot, user_id)
        return

    # Кнопка "Интересно!"
    if data == "btn_interesting":
        log_button_click("btn_interesting", user_id)
        await send_day0_and_day1_start(context.bot, user_id)
        return

    # Кнопка "Отлично, давай начнём!"
    if data == "btn_lets_go":
        log_button_click("btn_lets_go", user_id)
        set_course_started(user_id)
        await send_day1(context.bot, user_id)
        return

    # Кнопки со ссылками — логируем клик и открываем ссылку
    if data in BUTTON_URLS:
        log_button_click(data, user_id)
        url = BUTTON_URLS[data]
        name = BUTTON_NAMES[data]
        await query.message.reply_text(
            "Переходи по ссылке 👇",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(name, url=url)]])
        )
        return


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    s = get_stats()

    days_text = ""
    for day, count in s["days"].items():
        days_text += f"  День {day}: {count} чел.\n"

    clicks_text = ""
    for btn, count in s["clicks"].items():
        name = BUTTON_NAMES.get(btn, btn)
        clicks_text += f"  {name}: {count}\n"

    if not clicks_text:
        clicks_text = "  Пока нет кликов\n"

    text = (
        f"📊 Статистика бота\n\n"
        f"👥 Всего пользователей: {s['total']}\n"
        f"🆕 Новых за неделю: {s['new_week']}\n"
        f"🚫 Заблокировали бота: {s['blocked']}\n"
        f"❌ Не подписались и ушли: {s['not_subscribed']}\n"
        f"✅ Завершили серию (День 7): {s['completed']}\n\n"
        f"📅 По дням:\n{days_text}\n"
        f"🔘 Клики по кнопкам:\n{clicks_text}"
    )

    await update.message.reply_text(text)


async def fixdb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    # Исправляем все записи где start_date не похожа на правильную дату
    c.execute("SELECT user_id, start_date FROM users")
    rows = c.fetchall()
    fixed = 0
    for user_id, start_date in rows:
        if start_date and (len(str(start_date)) != 10 or not str(start_date).startswith('20')):
            c.execute("UPDATE users SET start_date = ? WHERE user_id = ?", (today, user_id))
            fixed += 1
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Исправлено записей: {fixed}\nУстановлена дата: {today}")


async def broadcast9_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассылка только тем кто прошёл 9+ дней"""
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    TEXT_BROADCAST9 = (
        "ПРИОТКРЫВАЮ ЗАВЕСУ ТАЙНЫ ⭐️\n\n"
        "<b>Погрузитесь в атмосферу группового сопровождения за 10 минут</b>\n\n"
        "В трёх коротких видео вы на практике увидите <b>три главных принципа</b>, которые я использую в групповом сопровождении:\n\n"
        "· Выбор\n"
        "· Личность\n"
        "· Сценарии\n\n"
        "Как это связано с питанием и похудением? Скорее <a href=\"https://t.me/myanutrition/2285\">включайте видео</a> и узнаете"
    )

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE last_day >= 9 AND blocked = 0")
    users = c.fetchall()
    conn.close()

    await update.message.reply_text(f"🚀 Начинаю рассылку для {len(users)} человек (last_day >= 9)...")

    sent = 0
    failed = 0
    for (user_id,) in users:
        try:
            await context.bot.send_message(user_id, TEXT_BROADCAST9, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            failed += 1
            logging.error(f"Ошибка рассылки для {user_id}: {e}")

    await update.message.reply_text(f"✅ Рассылка завершена!\nОтправлено: {sent}\nОшибок: {failed}")


async def broadcast7_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассылка только тем кто прошёл 7+ дней"""
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    TEXT_BROADCAST = (
        "Добрый вечер! Только что открылись продажи в групповое сопровождение. "
        "В листе ожидания 112 человек, поэтому занимайте место прямо сейчас\n\n"
        "В группе будет всего 6 девушек, которые решительно готовы наладить отношения с едой\n\n"
        "Через три месяца будете благодарны себе за это решение. До встречи в группе! 🙌"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Занять место", url="https://myanutrition.ru/group/#rec2372331003")]
    ])

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE last_day >= 7 AND blocked = 0")
    users = c.fetchall()
    conn.close()

    await update.message.reply_text(f"🚀 Начинаю рассылку для {len(users)} человек (last_day >= 7)...")

    sent = 0
    failed = 0
    for (user_id,) in users:
        try:
            await context.bot.send_message(user_id, TEXT_BROADCAST, reply_markup=kb)
            sent += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            failed += 1
            logging.error(f"Ошибка рассылки для {user_id}: {e}")

    await update.message.reply_text(f"✅ Рассылка завершена!\nОтправлено: {sent}\nОшибок: {failed}")


async def runnow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    await update.message.reply_text("🚀 Запускаю рассылку прямо сейчас...")
    await daily_job(context)
    await update.message.reply_text("✅ Рассылка завершена!")


async def test_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    user_id = update.effective_user.id
    await update.message.reply_text("🧪 Запускаю тестовый режим...")

    await send_welcome(context.bot, user_id)
    await asyncio.sleep(2)
    await send_day0_and_day1_start(context.bot, user_id)
    await asyncio.sleep(2)
    await send_day1(context.bot, user_id)

    for day in range(2, 8):
        await asyncio.sleep(2)
        await send_day(context.bot, user_id, day)

    await update.message.reply_text("✅ Тест завершён!")

# ==================== ЗАПУСК ====================

def main():
    logging.basicConfig(level=logging.INFO)
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test_mode))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("runnow", runnow_command))
    app.add_handler(CommandHandler("fixdb", fixdb_command))
    app.add_handler(CommandHandler("broadcast7", broadcast7_command))
    app.add_handler(CommandHandler("broadcast9", broadcast9_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    job_queue = app.job_queue
    now = datetime.now()
    target_time = now.replace(hour=SEND_HOUR, minute=SEND_MINUTE, second=0, microsecond=0)
    if now >= target_time:
        target_time += timedelta(days=1)
    delay = (target_time - now).total_seconds()
    job_queue.run_repeating(daily_job, interval=86400, first=delay)

    print("Бот запущен! ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
