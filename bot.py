import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, CHANNEL_USERNAME, CHANNEL_LINK, ADMIN_ID
from questions import QUESTIONS, SECTIONS, ANSWER_OPTIONS
from results import get_result
from database import init_db, log_event, get_stats

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ── Состояния ──────────────────────────────────────────────────────────────

class TestState(StatesGroup):
    waiting_subscription = State()
    answering = State()


# ── Вспомогательные функции ────────────────────────────────────────────────

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status not in ("left", "kicked")
    except Exception:
        return False


def question_keyboard(q_index: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=label,
            callback_data=f"ans:{q_index}:{score}"
        )]
        for label, score in ANSWER_OPTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subscribe_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Я подписалась", callback_data="check_sub")],
    ])


def result_keyboard(buttons: list) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None
    rows = [
        [InlineKeyboardButton(text=b["label"], url=b["url"], callback_data=b.get("cb"))]
        if b.get("cb") else
        [InlineKeyboardButton(text=b["label"], url=b["url"])]
        for b in buttons
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def section_header(q_index: int) -> str:
    for start, end, title in SECTIONS:
        if q_index == start:
            return f"\n<b>{title}</b>\n\n"
    return ""


async def send_question(chat_id: int, state: FSMContext, q_index: int):
    header = section_header(q_index)
    total = len(QUESTIONS)
    text = (
        f"{header}"
        f"<b>Вопрос {q_index + 1} из {total}</b>\n\n"
        f"{QUESTIONS[q_index]}"
    )
    msg = await bot.send_message(
        chat_id,
        text,
        parse_mode="HTML",
        reply_markup=question_keyboard(q_index),
    )
    await state.update_data(last_msg_id=msg.message_id)


# ── Хендлеры ───────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    log_event(user_id, "start")

    subscribed = await check_subscription(user_id)
    if subscribed:
        await start_test(message.chat.id, state, user_id)
    else:
        await state.set_state(TestState.waiting_subscription)
        await message.answer(
            "👋 Привет! Я помогу тебе оценить своё питание глазами нутрициолога.\n\n"
            "Тест состоит из 35 вопросов и займёт около 5–7 минут.\n\n"
            "Чтобы получить результат, нужно быть подписанной на канал 👇",
            reply_markup=subscribe_keyboard(),
        )


@dp.callback_query(F.data == "check_sub", TestState.waiting_subscription)
async def check_sub_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    subscribed = await check_subscription(user_id)

    if subscribed:
        await callback.message.edit_reply_markup(reply_markup=None)
        await start_test(callback.message.chat.id, state, user_id)
    else:
        # Фиксируем — человек так и не подписался
        log_event(user_id, "not_subscribed")
        await callback.answer(
            "Похоже, ты ещё не подписалась 🙈 Подпишись и нажми кнопку снова!",
            show_alert=True,
        )


async def start_test(chat_id: int, state: FSMContext, user_id: int):
    await state.set_state(TestState.answering)
    await state.update_data(q_index=0, scores=[], user_id=user_id)

    log_event(user_id, "test_started")

    await bot.send_message(
        chat_id,
        "✅ Отлично! Начинаем тест.\n\n"
        "<i>Отвечай честно — не про идеальную себя, а про реальные последние 3 месяца.</i>\n"
        "Если сомневаешься — выбирай тот вариант, который чаще всего описывает твои дни.",
        parse_mode="HTML",
    )
    await send_question(chat_id, state, 0)


@dp.callback_query(F.data.startswith("ans:"), TestState.answering)
async def handle_answer(callback: CallbackQuery, state: FSMContext):
    _, q_str, score_str = callback.data.split(":")
    q_index = int(q_str)
    score = int(score_str)

    data = await state.get_data()

    if q_index != data.get("q_index", 0):
        await callback.answer("Этот вопрос уже отвечен ✅")
        return

    await callback.answer()

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    scores = data.get("scores", [])
    scores.append(score)
    next_index = q_index + 1
    user_id = data.get("user_id", callback.from_user.id)

    if next_index < len(QUESTIONS):
        await state.update_data(q_index=next_index, scores=scores)
        await send_question(callback.message.chat.id, state, next_index)
    else:
        await state.clear()
        total = sum(scores)
        result = get_result(total)

        log_event(user_id, "test_finished")

        await bot.send_message(
            callback.message.chat.id,
            f"🏁 <b>Тест завершён!</b>\n\nТвой результат: <b>{total} баллов</b> из 210\n\n"
            + "─" * 30,
            parse_mode="HTML",
        )

        # Добавляем callback_data к кнопкам для трекинга
        buttons = result["buttons"]
        for b in buttons:
            if b["url"] == "https://planerka.app/yuliya-minchenko-rnhsmx":
                b["_track"] = "btn_individual"
            elif b["url"] == "https://t.me/+jeRJ8g609qllZWQy":
                b["_track"] = "btn_group"

        await bot.send_message(
            callback.message.chat.id,
            result["text"],
            parse_mode="HTML",
            reply_markup=build_result_keyboard(buttons, user_id),
            disable_web_page_preview=True,
        )


def build_result_keyboard(buttons: list, user_id: int) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None
    rows = []
    for b in buttons:
        track = b.get("_track", "")
        cb_data = f"track:{track}:{user_id}" if track else None
        btn = InlineKeyboardButton(text=b["label"], url=b["url"])
        rows.append([btn])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data.startswith("track:"))
async def track_button(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) >= 3:
        event = parts[1]
        user_id = int(parts[2])
        log_event(user_id, event)
    await callback.answer()


# ── Статистика ─────────────────────────────────────────────────────────────

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    s = get_stats()

    not_sub = s["start"] - s["test_started"]

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👤 Открыли бота:             <b>{s['start']}</b>\n"
        f"🔒 Не подписались:           <b>{not_sub}</b>\n"
        f"📝 Начали тест:              <b>{s['test_started']}</b>\n"
        f"✅ Прошли до конца:          <b>{s['test_finished']}</b>\n"
        f"📌 Записаться на разбор:     <b>{s['btn_individual']}</b>\n"
        f"👥 Лист ожидания группы:     <b>{s['btn_group']}</b>"
    )
    await message.answer(text, parse_mode="HTML")


# ── Запуск ─────────────────────────────────────────────────────────────────

async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
