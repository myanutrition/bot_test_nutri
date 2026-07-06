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
from database import init_db, log_event, get_stats, get_finished_users

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

AUDIO_BOT_MESSAGE = (
    "🎧 <b>Знаю, но не делаю</b>\n\n"
    "Ты только что честно оценила своё питание — это уже важный шаг.\n\n"
    "Но часто бывает так: понимаешь что хочешь изменить, а что-то всё равно мешает.\n\n"
    "Я записала для вас 7 коротких аудио о том, почему разобраться с питанием не получается, "
    "даже если вы уже много знаете. Эта серия основана на опыте работы с сотнями клиентов, "
    "которые столкнулись с такой проблемой.\n\n"
    '👉 <a href="https://t.me/mya_audiobot">Слушать бесплатно</a>'
)

BROADCAST_MESSAGE = (
    "Добрый вечер! Только что открылись продажи в групповое сопровождение. "
    "В листе ожидания 112 человек, поэтому занимайте место прямо сейчас 👇\n\n"
    "В группе будет всего 6 девушек, которые решительно готовы наладить отношения с едой\n\n"
    '<a href="https://myanutrition.ru/group/#rec2372331003">Занять место</a>\n\n'
    "Через три месяца будете благодарны себе за это решение. До встречи в группе! 🙌"
)


class TestState(StatesGroup):
    waiting_subscription = State()
    answering = State()


async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status not in ("left", "kicked")
    except Exception:
        return False


def question_keyboard(q_index: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"ans:{q_index}:{score}")]
        for label, score in ANSWER_OPTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subscribe_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Я подписалась", callback_data="check_sub")],
    ])


def section_header(q_index: int) -> str:
    for start, end, title in SECTIONS:
        if q_index == start:
            return f"\n<b>{title}</b>\n\n"
    return ""


async def send_question(chat_id: int, state: FSMContext, q_index: int):
    header = section_header(q_index)
    total = len(QUESTIONS)
    text = f"{header}<b>Вопрос {q_index + 1} из {total}</b>\n\n{QUESTIONS[q_index]}"
    msg = await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=question_keyboard(q_index))
    await state.update_data(last_msg_id=msg.message_id)


def build_result_keyboard(buttons: list) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=b["label"], url=b["url"])]
        for b in buttons
    ])


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
        log_event(user_id, "not_subscribed")
        await callback.answer("Похоже, ты ещё не подписалась 🙈 Подпишись и нажми кнопку снова!", show_alert=True)


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
            f"🏁 <b>Тест завершён!</b>\n\nТвой результат: <b>{total} баллов</b> из 210\n\n" + "─" * 30,
            parse_mode="HTML",
        )
        await bot.send_message(
            callback.message.chat.id,
            result["text"],
            parse_mode="HTML",
            reply_markup=build_result_keyboard(result["buttons"]),
            disable_web_page_preview=True,
        )
        await bot.send_message(
            callback.message.chat.id,
            AUDIO_BOT_MESSAGE,
            parse_mode="HTML",
        )


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    s = get_stats()
    not_sub = s["start"] - s["test_started"]
    await message.answer(
        "📊 <b>Статистика бота</b>\n\n"
        f"👤 Открыли бота:             <b>{s['start']}</b>\n"
        f"🔒 Не подписались:           <b>{not_sub}</b>\n"
        f"📝 Начали тест:              <b>{s['test_started']}</b>\n"
        f"✅ Прошли до конца:          <b>{s['test_finished']}</b>\n"
        f"📌 Записаться на разбор:     <b>{s['btn_individual']}</b>\n"
        f"👥 Лист ожидания группы:     <b>{s['btn_group']}</b>",
        parse_mode="HTML",
    )


@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    users = get_finished_users()
    if not users:
        await message.answer("Нет пользователей, прошедших тест.")
        return

    await message.answer(f"Начинаю рассылку для {len(users)} пользователей...")

    sent = 0
    failed = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, BROADCAST_MESSAGE, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await message.answer(f"✅ Рассылка завершена!\n\nОтправлено: {sent}\nНе доставлено: {failed}")


async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
