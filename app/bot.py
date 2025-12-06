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
from .rate_limiter import RateLimiter
from .backend_client import BackendClient
from .user_storage import UserStorage

rate_limiter = RateLimiter(per_minute=settings.rate_limit_per_minute)
backend = BackendClient()
user_storage = UserStorage()

# Хранилище состояний пользователей (ожидание email для регистрации)
user_states: dict[int, str] = {}

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
    masked = (
        (settings.telegram_bot_token[:6] + "…" + settings.telegram_bot_token[-4:])
        if settings.telegram_bot_token
        else "<none>"
    )
    logger.info("Bot is starting up (TOKEN loaded: %s)", masked)

async def on_shutdown() -> None:
    logger.info("Bot is shutting down")

async def cmd_start(message: types.Message) -> None:
    if not message.from_user:
        await message.answer("Ошибка: не удалось получить информацию о пользователе.")
        return
    
    telegram_user_id = message.from_user.id
    telegram_username = message.from_user.username
    name = message.from_user.full_name or "there"
    
    # Разделяем имя на first_name и last_name
    name_parts = name.split(" ", 1)
    first_name = name_parts[0] if name_parts else name
    last_name = name_parts[1] if len(name_parts) > 1 else None
    
    # Сначала проверяем, существует ли Telegram пользователь через GET
    telegram_user = await backend.get_telegram_user(telegram_user_id)
    
    # Если пользователь не найден (404), создаем его через POST
    if not telegram_user:
        telegram_user = await backend.create_or_get_telegram_user(
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            first_name=first_name,
            last_name=last_name
        )
        
        if not telegram_user:
            await message.answer(
                "❌ Ошибка при создании пользователя. Пожалуйста, попробуйте позже."
            )
            return
    
    logger.debug("Telegram user from create_or_get: %s", telegram_user)
    
    # Проверяем, связан ли Telegram пользователь с основным аккаунтом
    # Пробуем разные варианты названий полей
    backend_user_id = (
        telegram_user.get("user_id") 
        or telegram_user.get("backend_user_id")
        or telegram_user.get("linked_user_id")
    )
    
    if backend_user_id:
        # Пользователь уже связан с основным аккаунтом
        # Получаем токен через логин (нужно сохранить email/password в хранилище)
        # Или можно использовать существующий токен, если он есть
        token = user_storage.get_token(telegram_user_id)
        
        if not token:
            # Если нет токена, нужно запросить у пользователя email для логина
            # Или можно использовать другой механизм
            await message.answer(
                f"Привет, {name}! 👋\n"
                f"Ваш Telegram аккаунт уже связан с основным аккаунтом.\n\n"
                f"Для продолжения работы необходимо войти. Пожалуйста, используйте /login",
                reply_markup=main_keyboard(),
            )
        else:
            # Сохраняем данные в локальное хранилище
            user_storage.set(
                telegram_user_id=telegram_user_id,
                backend_user_id=backend_user_id,
                token=token,
                telegram_username=telegram_username
            )
            await message.answer(
                f"Привет, {name}! Добро пожаловать обратно! 👋\n"
                f"Я AI-ассистент для бизнеса. Отправьте мне сообщение, чтобы начать.\n"
                f"/help для списка команд.",
                reply_markup=main_keyboard(),
            )
    else:
        # Telegram пользователь не связан с основным аккаунтом
        # Проверяем локальное хранилище
        if user_storage.has_user(telegram_user_id):
            # Есть локальные данные, но не связаны в backend
            # Пытаемся связать
            local_backend_user_id = user_storage.get_backend_user_id(telegram_user_id)
            if local_backend_user_id:
                link_result = await backend.link_telegram_user(telegram_user_id, local_backend_user_id)
                if link_result:
                    await message.answer(
                        f"Привет, {name}! Добро пожаловать обратно! 👋\n"
                        f"Я AI-ассистент для бизнеса. Отправьте мне сообщение, чтобы начать.\n"
                        f"/help для списка команд.",
                        reply_markup=main_keyboard(),
                    )
                    return
        
        # Предлагаем регистрацию
        await message.answer(
            f"Привет, {name}! 👋\n"
            f"Я AI-ассистент для бизнеса.\n\n"
            f"Для начала работы необходимо создать аккаунт.\n\n"
            f"Хотите создать аккаунт?",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="✅ Создать аккаунт", callback_data="register_confirm"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="register_cancel")
                ]]
            ),
        )

async def cmd_help(message: types.Message) -> None:
    await message.answer(
        "Команды:\n"
        "/start - приветствие\n"
        "/help - эта справка\n"
        "/conversations - список разговоров\n"
        "/history - история текущего разговора\n"
        "/clear - очистить память разговора\n"
        "/templates - открыть шаблоны",
        reply_markup=main_keyboard(),
    )

async def cmd_conversations(message: types.Message) -> None:
    """Показывает список разговоров пользователя"""
    if not message.from_user:
        await message.answer("Ошибка: не удалось получить информацию о пользователе.")
        return
    
    telegram_user_id = message.from_user.id
    backend_user_id = user_storage.get_backend_user_id(telegram_user_id)
    
    if not backend_user_id:
        # Пытаемся получить из backend
        telegram_user = await backend.get_telegram_user(telegram_user_id)
        if telegram_user:
            backend_user_id = (
                telegram_user.get("user_id") 
                or telegram_user.get("backend_user_id")
                or telegram_user.get("linked_user_id")
            )
    
    if not backend_user_id:
        await message.answer(
            "❌ Вы не зарегистрированы. Пожалуйста, используйте /start для регистрации."
        )
        return
    
    await message.answer("⏳ Загружаю список разговоров...")
    
    conversations = await backend.get_conversations(backend_user_id)
    
    if conversations is None:
        await message.answer("❌ Ошибка при получении списка разговоров.")
        return
    
    if not conversations:
        await message.answer(
            "📭 У вас пока нет разговоров.\n\n"
            "Начните новый разговор, отправив сообщение боту."
        )
        return
    
    # Создаем клавиатуру с разговорами
    keyboard_rows = []
    for conv in conversations:
        conv_id = conv.get("id") or conv.get("conversation_id")
        title = conv.get("title") or conv.get("name") or f"Разговор #{conv_id}"
        # Ограничиваем длину названия для кнопки
        button_text = title[:40] + "..." if len(title) > 40 else title
        keyboard_rows.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"conv|{conv_id}"
            )
        ])
    
    # Добавляем кнопку "Новый разговор"
    keyboard_rows.append([
        InlineKeyboardButton(text="➕ Новый разговор", callback_data="conv|new")
    ])
    
    await message.answer(
        f"📋 Ваши разговоры ({len(conversations)}):\n\n"
        f"Выберите разговор для просмотра или создания нового:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )

async def cmd_history(message: types.Message) -> None:
    """Показывает историю текущего разговора"""
    if not message.from_user:
        await message.answer("Ошибка: не удалось получить информацию о пользователе.")
        return
    
    telegram_user_id = message.from_user.id
    conversation_id = user_storage.get_conversation_id(telegram_user_id)
    
    if not conversation_id:
        await message.answer(
            "❌ У вас нет активного разговора.\n\n"
            "Используйте /conversations для выбора разговора или начните новый, отправив сообщение."
        )
        return
    
    await message.answer("⏳ Загружаю историю разговора...")
    
    history = await backend.get_conversation_history(conversation_id)
    
    if history is None:
        await message.answer("❌ Ошибка при получении истории разговора.")
        return
    
    if not history:
        await message.answer("📭 История разговора пуста.")
        return
    
    # Форматируем историю
    history_text = "📜 История разговора:\n\n"
    
    # Получаем title разговора (если есть)
    title = None
    for msg in history:
        if msg.get("title"):
            title = msg.get("title")
            break
    
    if title:
        history_text += f"**{title}**\n\n"
    
    # Форматируем сообщения
    for msg in history:
        role = msg.get("role") or msg.get("name") or "user"
        content = msg.get("content") or msg.get("message") or msg.get("text") or ""
        
        # Определяем имя отправителя
        if role.lower() in ["user", "human"]:
            name = "Вы"
        elif role.lower() in ["assistant", "ai", "bot"]:
            name = "Ассистент"
        else:
            name = role.capitalize()
        
        history_text += f"{name}:\n{content}\n\n"
    
    # Разбиваем на части, если сообщение слишком длинное
    if len(history_text) > 4000:
        # Отправляем частями
        parts = [history_text[i:i+4000] for i in range(0, len(history_text), 4000)]
        for part in parts:
            await message.answer(part, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer(history_text, parse_mode=ParseMode.MARKDOWN)

async def cmd_clear(message: types.Message) -> None:
    # Очищаем текущий разговор (сбрасываем conversation_id)
    if message.from_user:
        user_storage.set_conversation_id(message.from_user.id, None)
    await message.answer("✅ Текущий разговор сброшен. Новое сообщение начнет новый разговор.", reply_markup=main_keyboard())


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
    # Получаем backend_user_id из Telegram пользователя или локального хранилища
    backend_user_id = None
    
    # Сначала проверяем локальное хранилище
    if user_storage.has_user(user_id):
        backend_user_id = user_storage.get_backend_user_id(user_id)
    
    # Если нет в локальном хранилище, проверяем через GET, затем создаем через POST если нужно
    if not backend_user_id:
        try:
            # Сначала проверяем через GET, существует ли пользователь в таблице telegram_users
            telegram_user = await backend.get_telegram_user(user_id)
            
            # Если пользователь не найден (404), создаем его через POST
            if not telegram_user:
                logger.info("Telegram user %s not found, creating via POST", user_id)
                telegram_user = await backend.create_or_get_telegram_user(
                    telegram_user_id=user_id,
                    telegram_username=telegram_username,
                    first_name=first_name,
                    last_name=last_name
                )
            
            if telegram_user:
                logger.info("Telegram user response: %s", telegram_user)
                # Пробуем разные варианты названий полей
                backend_user_id = (
                    telegram_user.get("user_id") 
                    or telegram_user.get("backend_user_id")
                    or telegram_user.get("linked_user_id")
                )
                logger.info("Extracted backend_user_id: %s from telegram_user: %s", backend_user_id, telegram_user)
                
                # Если нашли в backend, сохраняем в локальное хранилище
                if backend_user_id:
                    token = user_storage.get_token(user_id)
                    user_storage.set(
                        telegram_user_id=user_id,
                        backend_user_id=backend_user_id,
                        token=token,  # Сохраняем токен, если есть
                        telegram_username=telegram_user.get("telegram_username")
                    )
                else:
                    # Telegram пользователь существует, но не связан с основным аккаунтом
                    # Пробуем использовать telegram_user_id напрямую для отправки сообщений
                    logger.info("Telegram user %s exists but not linked to backend account, using telegram_user_id directly", user_id)
                    backend_user_id = user_id  # Используем telegram_user_id как user_id
                    # Сохраняем в локальное хранилище для будущих запросов
                    user_storage.set(
                        telegram_user_id=user_id,
                        backend_user_id=user_id,  # Временно используем telegram_user_id
                        telegram_username=telegram_user.get("telegram_username")
                    )
            else:
                logger.warning("Failed to get/create Telegram user %s", user_id)
        except Exception as e:
            logger.exception("Error getting/creating Telegram user: %s", e)
    
    # Если все еще нет backend_user_id, пользователь не зарегистрирован
    if not backend_user_id:
        await bot.send_message(
            chat_id,
            "❌ Вы не зарегистрированы. Пожалуйста, используйте /start для регистрации."
        )
        return
    
    if not rate_limiter.allow(user_id):
        await bot.send_message(chat_id, "Превышен лимит запросов. Попробуйте позже.")
        return

    # Получаем текущий conversation_id
    conversation_id = user_storage.get_conversation_id(user_id)
    logger.info("Sending message with conversation_id: %s (user_id: %s)", conversation_id, user_id)
    
    async with ChatActionSender.typing(bot=bot, chat_id=chat_id):
        try:
            reply_data = await backend.send_message(backend_user_id, text, conversation_id)
            if reply_data is None:
                await bot.send_message(chat_id, "Ошибка при обращении к серверу. Попробуйте позже.")
                return
            
            logger.info("Backend response: %s", reply_data)
            
            # Проверяем, вернул ли backend conversation_id в ответе
            # (если это новый разговор, backend может вернуть его ID)
            new_conversation_id = None
            reply = None
            
            if isinstance(reply_data, dict):
                # Пробуем разные варианты названий полей для conversation_id
                new_conversation_id = (
                    reply_data.get("conversation_id") 
                    or reply_data.get("conversationId")
                    or reply_data.get("id")
                    or reply_data.get("conversation_id")
                )
                
                # Конвертируем в int, если это строка
                if new_conversation_id is not None:
                    try:
                        new_conversation_id = int(new_conversation_id)
                    except (ValueError, TypeError):
                        logger.warning("Invalid conversation_id format: %s", new_conversation_id)
                        new_conversation_id = None
                
                if new_conversation_id:
                    logger.info("New conversation_id received: %s", new_conversation_id)
                    user_storage.set_conversation_id(user_id, new_conversation_id)
                
                # Извлекаем текст ответа
                reply = (
                    reply_data.get("response") 
                    or reply_data.get("message") 
                    or reply_data.get("text")
                    or reply_data.get("content")
                    or reply_data.get("answer")
                )
            else:
                reply = reply_data
                
        except Exception as e:
            logger.exception("Backend call failed: %s", e)
            await bot.send_message(chat_id, "Ошибка сервера. Попробуйте позже.")
            return
    
    if not reply:
        await bot.send_message(chat_id, "Ошибка: пустой ответ от сервера.")
        return
    
    reply = _clean_markdown(reply)
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
    
    # Обработка выбора разговора
    if data.startswith("conv|"):
        if not call.from_user:
            await call.answer("Ошибка: не удалось получить информацию о пользователе.", show_alert=True)
            return
        
        _, conv_data = data.split("|", 1)
        telegram_user_id = call.from_user.id
        
        if conv_data == "new":
            # Создаем новый разговор (сбрасываем conversation_id)
            user_storage.set_conversation_id(telegram_user_id, None)
            await call.message.edit_text(
                "✅ Новый разговор создан.\n\n"
                "Отправьте сообщение, чтобы начать новый разговор."
            )
            await call.answer("Новый разговор создан")
            return
        
        try:
            conversation_id = int(conv_data)
        except ValueError:
            await call.answer("Ошибка: неверный ID разговора", show_alert=True)
            return
        
        # Устанавливаем выбранный разговор как текущий
        user_storage.set_conversation_id(telegram_user_id, conversation_id)
        
        # Загружаем и показываем историю разговора
        await call.message.edit_text("⏳ Загружаю историю разговора...")
        
        history = await backend.get_conversation_history(conversation_id)
        
        if history is None:
            await call.message.edit_text("❌ Ошибка при получении истории разговора.")
            await call.answer("Ошибка", show_alert=True)
            return
        
        if not history:
            await call.message.edit_text(
                "📭 История разговора пуста.\n\n"
                "Отправьте сообщение, чтобы начать разговор."
            )
            await call.answer("Разговор выбран")
            return
        
        # Форматируем историю
        history_text = "📜 История разговора:\n\n"
        
        # Получаем title разговора (если есть)
        title = None
        for msg in history:
            if msg.get("title"):
                title = msg.get("title")
                break
        
        if title:
            history_text += f"**{title}**\n\n"
        
        # Форматируем сообщения
        for msg in history:
            role = msg.get("role") or msg.get("name") or "user"
            content = msg.get("content") or msg.get("message") or msg.get("text") or ""
            
            # Определяем имя отправителя
            if role.lower() in ["user", "human"]:
                name = "Вы"
            elif role.lower() in ["assistant", "ai", "bot"]:
                name = "Ассистент"
            else:
                name = role.capitalize()
            
            history_text += f"{name}:\n{content}\n\n"
        
        # Разбиваем на части, если сообщение слишком длинное
        if len(history_text) > 4000:
            # Отправляем первую часть
            first_part = history_text[:4000]
            await call.message.edit_text(first_part, parse_mode=ParseMode.MARKDOWN)
            # Остальные части отправляем отдельными сообщениями
            remaining = history_text[4000:]
            parts = [remaining[i:i+4000] for i in range(0, len(remaining), 4000)]
            for part in parts:
                await call.message.answer(part, parse_mode=ParseMode.MARKDOWN)
        else:
            await call.message.edit_text(history_text, parse_mode=ParseMode.MARKDOWN)
        
        await call.answer("Разговор выбран")
        return
    
    # Обработка регистрации
    if data == "register_confirm":
        if not call.from_user:
            await call.answer("Ошибка: не удалось получить информацию о пользователе.", show_alert=True)
            return
        
        telegram_user_id = call.from_user.id
        telegram_username = call.from_user.username
        name = call.from_user.full_name or "Пользователь"
        
        # Проверяем, не зарегистрирован ли уже
        if user_storage.has_user(telegram_user_id):
            await call.answer("Вы уже зарегистрированы!", show_alert=True)
            await call.message.edit_text(
                f"Привет, {name}! 👋\n"
                f"Вы уже зарегистрированы. Отправьте мне сообщение, чтобы начать.\n"
                f"/help для списка команд."
            )
            return
        
        # Автоматически генерируем email и регистрируем пользователя
        await call.message.edit_text("⏳ Создаю аккаунт...")
        
        # Генерируем email автоматически
        email = backend._generate_email(telegram_user_id, telegram_username)
        password = backend._generate_password()
        
        try:
            result = await backend.register(
                email=email,
                password=password,
                business_type="other",
                telegram_username=telegram_username,
                full_name=name
            )
            
            if result:
                backend_user_id = result.get("user_id")
                token = result.get("token")
                
                # Связываем Telegram пользователя с основным аккаунтом
                link_result = await backend.link_telegram_user(telegram_user_id, backend_user_id)
                
                if not link_result:
                    logger.warning("Failed to link telegram user %s to backend user %s", telegram_user_id, backend_user_id)
                
                # Сохраняем данные
                user_storage.set(
                    telegram_user_id=telegram_user_id,
                    backend_user_id=backend_user_id,
                    token=token,
                    email=email,
                    password=password,
                    telegram_username=telegram_username
                )
                
                await call.message.edit_text(
                    f"✅ Аккаунт успешно создан!\n\n"
                    f"Привет, {name}! 👋\n"
                    f"Я AI-ассистент для бизнеса. Отправьте мне сообщение, чтобы начать.\n"
                    f"/help для списка команд."
                )
                await call.answer("Регистрация успешна! ✅")
            else:
                await call.message.edit_text(
                    "❌ Ошибка при создании аккаунта. Пожалуйста, попробуйте позже или используйте /start."
                )
                await call.answer("Ошибка регистрации", show_alert=True)
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower() or "exists" in error_msg.lower():
                await call.message.edit_text(
                    "❌ Пользователь с таким Telegram username уже существует.\n\n"
                    "Пожалуйста, обратитесь в поддержку."
                )
            else:
                logger.exception("Registration error: %s", e)
                await call.message.edit_text(
                    "❌ Ошибка при создании аккаунта. Пожалуйста, попробуйте позже."
                )
            await call.answer("Ошибка регистрации", show_alert=True)
        return
    
    if data == "register_cancel":
        if call.from_user:
            user_states.pop(call.from_user.id, None)
        await call.message.edit_text(
            "Регистрация отменена. Используйте /start для начала работы."
        )
        await call.answer("Регистрация отменена")
        return
    
    # Обработка шаблонов
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
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    if not message.from_user:
        await message.answer("Ошибка: не удалось получить информацию о пользователе.")
        return
    
    uid = message.from_user.id
    telegram_username = message.from_user.username
    name = message.from_user.full_name or ""
    name_parts = name.split(" ", 1)
    first_name = name_parts[0] if name_parts else None
    last_name = name_parts[1] if len(name_parts) > 1 else None
    
    # Обычная обработка сообщений
    await _process_text(message.bot, message.chat.id, uid, message.text, telegram_username, first_name, last_name)

async def main() -> None:
    if not settings.telegram_bot_token:
        logger.error("Env var TELEGRAM_BOT_TOKEN not found. Ensure it is set in deployment service variables.")
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_conversations, Command("conversations"))
    dp.message.register(cmd_history, Command("history"))
    dp.message.register(cmd_clear, Command("clear"))
    dp.message.register(open_templates, Command("templates"))
    dp.message.register(open_templates, F.text == "Шаблоны")
    dp.callback_query.register(on_callback)
    dp.message.register(handle_message)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
