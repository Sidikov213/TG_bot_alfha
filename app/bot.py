import asyncio
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.utils.chat_action import ChatActionSender
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.types import ForceReply, CallbackQuery

from .config import settings
from .logger import logger
from .memory import ConversationMemory
from .rate_limiter import RateLimiter
from .ai_client import AIClient

memory = ConversationMemory(max_messages=settings.max_history_messages)
rate_limiter = RateLimiter(per_minute=settings.rate_limit_per_minute)
ai = AIClient()

CATEGORIES: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Финансы",
        [
            ("Смета/калькуляция", "Составь детальную смету для услуги: [опишите услугу]. Включи материалы, работу, налоги, наценку, итоговую стоимость и срок выполнения."),
            ("Счёт/Инвойс", "Составь инвойс для клиента [Имя/Компания] за услугу [название], с позициями, количеством, ставкой, итогом и сроком оплаты."),
            ("План платежей", "Составь график платежей по договору на период [период], укажи суммы, даты оплаты и напоминания."),
            ("Бюджет на месяц", "Составь бюджет микробизнеса в нише [ниша] на месяц с категориями затрат, доходами и целевыми KPI."),
        ],
    ),
    (
        "Клиенты",
        [
            ("Коммерческое предложение", "Сформируй коммерческое предложение для клиента [Имя/Компания] на услугу [название], с вариантами пакетов, сроками, гарантиями и CTA."),
            ("Скрипт звонка", "Напиши короткий скрипт входящего звонка для микробизнеса в нише [ниша], цель — квалификация и запись на консультацию."),
            ("Email клиенту", "Напиши письмо клиенту с подтверждением заказа [описание], сроками выполнения, контактами и следующими шагами."),
            ("Ответ на возражение", "Сформулируй ответы на типовые возражения клиента в нише [ниша] с 3 вариантами формулировок."),
        ],
    ),
    (
        "Договоры",
        [
            ("Договор (черновик)", "Сгенерируй черновик договора на оказание услуг [описание], с предметом, сроками, оплатой, ответственностью, форс-мажором и реквизитами."),
            ("Политика возврата", "Сформулируй политику возвратов для малого бизнеса в сфере [сфера], с условиями сроков, состоянием товара/услуги и порядком обращения."),
            ("Оферта", "Подготовь публичную оферту на услугу [название] с описанием услуг, условий оплаты, ответственности и порядка расторжения."),
        ],
    ),
    (
        "Операции",
        [
            ("Бриф", "Составь бриф для клиента в нише [ниша] с вопросами по целям, аудитории, бюджету, срокам и критериям успеха."),
            ("Регламент", "Напиши регламент обработки заявки: шаги, SLA по времени, ответственные и точки контроля качества."),
            ("План продвижения", "Составь 4-недельный план продвижения для микробизнеса в нише [ниша] с каналами, бюджетами и KPI."),
        ],
    ),
]


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Шаблоны")]],
        resize_keyboard=True,
        input_field_placeholder="Напишите вопрос или откройте шаблоны",
    )

async def on_startup() -> None:
    logger.info("Bot is starting up")

async def on_shutdown() -> None:
    logger.info("Bot is shutting down")

async def cmd_start(message: types.Message) -> None:
    name = message.from_user.full_name if message.from_user else "there"
    await message.answer(
        f"Hi, {name}! I am an AI assistant. Send me a message to begin.\n"
        f"/help for options.",
        reply_markup=main_keyboard(),
    )

async def cmd_help(message: types.Message) -> None:
    await message.answer(
        "Commands:\n"
        "/start - greeting\n"
        "/help - this help\n"
        "/clear - clear your conversation memory\n"
        "/templates - open templates",
        reply_markup=main_keyboard(),
    )

async def cmd_clear(message: types.Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    memory.clear(uid)
    await message.answer("Memory cleared.", reply_markup=main_keyboard())


def _clean_markdown(text: str) -> str:
    lines = text.splitlines()
    cleaned: list[str] = []
    for line in lines:
        line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)
        line = re.sub(r"^\s{0,3}[-*]\s+", "• ", line)
        line = re.sub(r"^\s{0,3}>\s?", "", line)
        line = line.replace("**", "").replace("__", "").replace("*", "")
        line = line.replace("```", "").replace("`", "")
        cleaned.append(line)
    result = "\n".join(cleaned)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    return result


async def _process_text(bot: Bot, chat_id: int, user_id: int, text: str) -> None:
    if not rate_limiter.allow(user_id):
        await bot.send_message(chat_id, "Rate limit exceeded. Please try again later.")
        return
    msgs = [{"role": "system", "content": settings.system_prompt}]
    for role, content in memory.get(user_id):
        msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": text})

    async with ChatActionSender.typing(bot=bot, chat_id=chat_id):
        try:
            reply = await ai.chat(msgs)
        except Exception as e:
            logger.exception("AI call failed: %s", e)
            await bot.send_message(chat_id, "AI error. Please try again.")
            return
    reply = _clean_markdown(reply)
    memory.add(user_id, "user", text)
    memory.add(user_id, "assistant", reply)
    await bot.send_message(chat_id, reply, parse_mode=ParseMode.HTML)


def categories_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for idx, (cat, _) in enumerate(CATEGORIES):
        row.append(InlineKeyboardButton(text=cat, callback_data=f"cat|{idx}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def templates_keyboard_by_category(cat_idx: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    _, templates = CATEGORIES[cat_idx]
    for tidx, (title, _text) in enumerate(templates):
        row.append(InlineKeyboardButton(text=title, callback_data=f"tpl|{cat_idx}|{tidx}"))
        if len(row) == 1:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Категории", callback_data="back|cats")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def open_templates(message: types.Message) -> None:
    await message.answer(
        "Выберите категорию шаблонов",
        reply_markup=categories_keyboard(),
    )


async def on_callback(call: CallbackQuery) -> None:
    data = call.data or ""
    if data.startswith("cat|"):
        _, sidx = data.split("|", 1)
        idx = int(sidx)
        await call.message.edit_text("Выберите шаблон", reply_markup=templates_keyboard_by_category(idx))
        await call.answer()
        return
    if data.startswith("back|cats"):
        await call.message.edit_text("Выберите категорию шаблонов", reply_markup=categories_keyboard())
        await call.answer()
        return
    if data.startswith("tpl|"):
        _, cidx, tidx = data.split("|", 2)
        ci = int(cidx)
        ti = int(tidx)
        title, text = CATEGORIES[ci][1][ti]
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Вставить в поле ввода", switch_inline_query_current_chat=text)],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat|{ci}")],
            ]
        )
        await call.message.edit_text(
            f"{title}:\n\n{text}",
            reply_markup=kb,
        )
        await call.answer()
        return

async def handle_message(message: types.Message) -> None:
    if not message.text:
        await message.answer("Please send text.")
        return
    uid = message.from_user.id if message.from_user else 0
    await _process_text(message.bot, message.chat.id, uid, message.text)

async def main() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_clear, Command("clear"))
    dp.message.register(open_templates, Command("templates"))
    dp.message.register(open_templates, F.text == "Шаблоны")
    dp.callback_query.register(on_callback)
    dp.message.register(handle_message)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
