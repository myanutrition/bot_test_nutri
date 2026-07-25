# -*- coding: utf-8 -*-
import asyncio
import logging
import os

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.exceptions import TelegramBadRequest

import config
import user_state
from quiz_data import QUESTIONS, INTRO_TEXT, get_result
from database import (
    log_event,
    get_stats,
    get_completed_users,
    EVENT_BOT_OPENED,
    EVENT_QUIZ_STARTED,
    EVENT_QUIZ_COMPLETED,
    EVENT_GROUP_CLICKED,
    EVENT_PODCAST_CLICKED,
)

router = Router()
logger = logging.getLogger(__name__)

TOTAL = len(QUESTIONS)
NOT_MEMBER_STATUSES = {"left", "kicked"}

BROADCAST_TEXT = (
    "Добрый вечер! Только что открылись продажи в групповое сопровождение. "
    "В листе ожидания 112 человек, поэтому занимайте место прямо сейчас 👇\n\n"
    "В группе будет всего 6 девушек, которые решительно готовы наладить отношения с едой\n\n"
    '<a href="https://myanutrition.ru/group/#rec2372331003">Занять место</a>\n\n'
    "Через три месяца будете благодарны себе за это решение. До встречи в группе! 🙌"
)


# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------

def _start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🚀 Начать", callback_data="begin_flow")]]
    )


def _check_sub_kb() -> InlineKeyboardMarkup:
    channel = config.CHANNEL_USERNAME.lstrip("@")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Перейти на канал", url=f"https://t.me/{channel}")],
            [InlineKeyboardButton(text="✅ Я подписалась", callback_data="begin_flow")],
        ]
    )


def _question_kb(index: int) -> InlineKeyboardMarkup:
    q = QUESTIONS[index]
    letters = list(q["options"].keys())
    buttons = [
        InlineKeyboardButton(text=letter, callback_data=f"ans:{index}:{letter}")
        for letter in letters
    ]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _next_kb(index: int) -> InlineKeyboardMarkup:
    is_last = index == TOTAL - 1
    label = "Показать результат 🎉" if is_last else "Следующий вопрос ➡️"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=f"next:{index}")]]
    )


def _podcast_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text="🎙 Слушать подкаст",
            callback_data="podcast_click"
        )]]
    )


def _group_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text="🌿 Узнать о групповом сопровождении",
            callback_data="group_click"
        )]]
    )


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def cmd_start(message: Message):
    log_event(message.from_user.id, EVENT_BOT_OPENED)

    photo = None
    if config.START_PHOTO_FILE_ID:
        photo = config.START_PHOTO_FILE_ID
    elif os.path.exists(config.START_PHOTO_PATH):
        photo = FSInputFile(config.START_PHOTO_PATH)

    if photo:
        await message.answer_photo(
            photo=photo, caption=INTRO_TEXT, reply_markup=_start_kb(), parse_mode="HTML"
        )
    else:
        await message.answer(INTRO_TEXT, reply_markup=_start_kb(), parse_mode="HTML")


# ---------------------------------------------------------------------------
# Проверка подписки
# ---------------------------------------------------------------------------

async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=config.CHANNEL_USERNAME, user_id=user_id)
        return member.status not in NOT_MEMBER_STATUSES
    except TelegramBadRequest as e:
        logger.error("Не удалось проверить подписку: %s", e)
        return False


@router.callback_query(F.data == "begin_flow")
async def on_begin_flow(callback: CallbackQuery):
    is_subscribed = await check_subscription(callback.bot, callback.from_user.id)
    await callback.answer()

    if is_subscribed:
        await callback.message.answer("✅ Подписка подтверждена! Начинаем тест.")
        await send_question(callback.message, callback.from_user.id, first=True)
    else:
        await callback.message.answer(
            "Чтобы пройти тест, подпишись на канал 👇",
            reply_markup=_check_sub_kb()
        )


# ---------------------------------------------------------------------------
# Тест
# ---------------------------------------------------------------------------

async def send_question(message: Message, user_id: int, first: bool = False):
    if first:
        user_state.start_quiz(user_id)
        log_event(user_id, EVENT_QUIZ_STARTED)

    index = user_state.get_current_index(user_id)
    q = QUESTIONS[index]

    options_text = "\n".join(f"{letter}. {text}" for letter, text in q["options"].items())
    text = (
        f"<b>Вопрос {index + 1} из {TOTAL}</b>\n\n"
        f"{q['question']}\n\n"
        f"{options_text}"
    )
    await message.answer(text, reply_markup=_question_kb(index), parse_mode="HTML")


@router.callback_query(F.data.startswith("ans:"))
async def on_answer(callback: CallbackQuery):
    _, idx_str, letter = callback.data.split(":")
    index = int(idx_str)
    q = QUESTIONS[index]
    correct = q["correct"]
    is_correct = letter == correct

    user_state.register_answer(callback.from_user.id, is_correct)
    await callback.answer("Верно! ✅" if is_correct else f"Правильный ответ: {correct}")

    verdict = "✅ Верно!" if is_correct else f"Правильный ответ: <b>{correct}</b>"
    text = f"{verdict}\n\n<b>Разбор:</b>\n{q['explanation']}"
    await callback.message.answer(text, reply_markup=_next_kb(index), parse_mode="HTML")


@router.callback_query(F.data.startswith("next:"))
async def on_next(callback: CallbackQuery):
    _, idx_str = callback.data.split(":")
    index = int(idx_str)
    user_id = callback.from_user.id
    await callback.answer()

    if index >= TOTAL - 1:
        # Тест завершён
        log_event(user_id, EVENT_QUIZ_COMPLETED)
        score = user_state.get_score(user_id)
        user_state.clear(user_id)

        result = get_result(score)

        # Результат
        result_text = (
            f"🎯 <b>Ваш результат: {score} из {TOTAL}</b>\n\n"
            f"{result['emoji']} <b>{result['title']}</b>\n\n"
            f"{result['body']}"
        )
        await callback.message.answer(result_text, parse_mode="HTML")

        # Подкасты
        await asyncio.sleep(1)
        podcasts = result["podcasts"]
        podcast_lines = "\n".join(f'• <a href="{url}">{title}</a>' for title, url in podcasts)
        podcast_text = f"🎙 <b>Выпуски подкаста под ваш результат:</b>\n\n{podcast_lines}"
        await callback.message.answer(
            podcast_text,
            reply_markup=_podcast_kb(),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

        # Группа (только для 0–6 баллов)
        if result["group"]:
            await asyncio.sleep(1)
            group_text = (
                "🌿 <b>Групповое сопровождение</b>\n\n"
                "Если хочется не просто понимать, а реально изменить питание — "
                "я приглашаю вас в групповое сопровождение.\n\n"
                "Небольшая группа, работа с тем, что мешает именно вам, "
                "поддержка на каждом шаге."
            )
            await callback.message.answer(
                group_text,
                reply_markup=_group_kb(),
                parse_mode="HTML",
            )
    else:
        user_state.advance(user_id)
        await send_question(callback.message, user_id)


@router.callback_query(F.data == "podcast_click")
async def on_podcast_click(callback: CallbackQuery):
    log_event(callback.from_user.id, EVENT_PODCAST_CLICKED)
    await callback.answer()
    await callback.message.answer(
        "Все выпуски здесь 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🎙 Открыть подкаст", url=config.PODCAST_URL)
        ]])
    )


@router.callback_query(F.data == "group_click")
async def on_group_click(callback: CallbackQuery):
    log_event(callback.from_user.id, EVENT_GROUP_CLICKED)
    await callback.answer()
    await callback.message.answer(
        "Узнать подробнее и записаться 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🌿 Перейти на сайт", url=config.GROUP_URL)
        ]])
    )


# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return

    s = get_stats()
    not_sub = s["opened"] - s["started"]
    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👤 Открыли бота:          <b>{s['opened']}</b>\n"
        f"🔒 Не подписались:        <b>{not_sub}</b>\n"
        f"📝 Начали тест:           <b>{s['started']}</b>\n"
        f"✅ Прошли до конца:       <b>{s['completed']}</b>\n"
        f"🎙 Кликнули подкаст:      <b>{s['podcast_clicks']}</b>\n"
        f"🌿 Кликнули группу:       <b>{s['group_clicks']}</b>"
    )
    await message.answer(text, parse_mode="HTML")


# ---------------------------------------------------------------------------
# /broadcast
# ---------------------------------------------------------------------------

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return

    users = get_completed_users()
    if not users:
        await message.answer("Нет пользователей, прошедших тест.")
        return

    await message.answer(f"Начинаю рассылку для {len(users)} пользователей...")

    sent, failed = 0, 0
    for user_id in users:
        try:
            await message.bot.send_message(
                user_id, BROADCAST_TEXT, parse_mode="HTML"
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await message.answer(
        f"✅ Рассылка завершена!\n\nОтправлено: {sent}\nНе доставлено: {failed}"
    )
