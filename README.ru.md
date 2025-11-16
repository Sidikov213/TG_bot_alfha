# Telegram AI Bot (aiogram)

Бизнес‑ассистент в Telegram, который отвечает с помощью AI (OpenAI / OpenRouter / Groq), запоминает контекст диалога, ограничивает частоту запросов и предоставляет шаблоны для типовых бизнес‑задач (финансы, клиенты, договоры, операции).

Бот написан на Python с использованием `aiogram v3`, асинхронных HTTP‑запросов и простой in‑memory памяти.

---

## Возможности

- **Базовые команды**
  - `/start` — приветствие и краткое описание возможностей бота  
  - `/help` — список команд  
  - `/clear` — очистка истории диалога для текущего пользователя  
  - `/templates` или кнопка «Шаблоны» — открытие набора готовых промптов  

- **AI‑чат**
  - Ответы ассистента через AI‑модель (OpenAI, OpenRouter или Groq через совместимый Chat Completions API)
  - **Память диалога** на пользователя: бот учитывает последние сообщения (до `MAX_HISTORY_MESSAGES`)  
  - Системный промпт задаётся через переменную `SYSTEM_PROMPT`

- **Шаблоны для бизнеса**
  - Категории:
    - Финансы (смета, инвойсы, план платежей, бюджет)
    - Клиенты (коммерческое предложение, скрипт звонка, e‑mail, ответы на возражения)
    - Договоры (черновик договора, политика возврата, оферта)
    - Операции (бриф, регламенты, план продвижения)
  - Возможность «вставить» шаблон прямо в поле ввода одним нажатием

- **Ограничение частоты запросов**
  - Простая реализация rate limit: максимум `RATE_LIMIT_PER_MINUTE` сообщений в минуту на пользователя

- **Логирование**
  - Структурированные логи запуска/остановки бота и ошибок AI

- **Инфраструктура**
  - Dockerfile для удобного деплоя
  - Конфигурация через `.env`

---

## Технологический стек

- **Язык**: Python 3.11+
- **Telegram‑фреймворк**: [aiogram v3](https://docs.aiogram.dev/)
- **AI‑клиент**: любой провайдер с OpenAI‑совместимым Chat Completions API:
  - OpenAI (`https://api.openai.com/v1`)
  - OpenRouter (`https://openrouter.ai/api/v1`)
  - Groq (`https://api.groq.com/openai/v1`)
- **Конфигурация**: `pydantic-settings`
- **HTTP‑клиент**: `httpx` (async)
- **Логирование**: стандартный модуль `logging`
- **Память диалога**: in‑memory (словарь + `deque`)
- **Ограничение частоты**: in‑memory rate limiter

---

## Быстрый старт (Windows)

### 1. Требования

- Установленный **Python 3.11+**
- Установленный **Git** (по желанию)
- Аккаунт и API‑ключ у выбранного AI‑провайдера
- Созданный Telegram‑бот и его токен (BotFather)

### 2. Клонирование и установка зависимостей

```bash
git clone https://github.com/Sidikov213/TG_bot_alfha.git
cd TG_bot_alfha

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

*(Путь к репозиторию замени на свой актуальный.)*

### 3. Настройка окружения

Скопируй шаблон:

```bash
copy env.example .env
```

Отредактируй `.env` и заполни ключевые переменные:

```env
TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН_БОТА

AI_PROVIDER=openai           # или openrouter / groq
AI_API_KEY=ВАШ_API_КЛЮЧ
AI_MODEL=gpt-4o-mini         # или другая модель провайдера
AI_BASE_URL=https://api.openai.com/v1
```

Примеры конфигураций:

- **OpenAI:**

  ```env
  AI_PROVIDER=openai
  AI_BASE_URL=https://api.openai.com/v1
  AI_MODEL=gpt-4o-mini
  ```

- **OpenRouter:**

  ```env
  AI_PROVIDER=openrouter
  AI_BASE_URL=https://openrouter.ai/api/v1
  AI_MODEL=openrouter/auto
  ```

- **Groq:**

  ```env
  AI_PROVIDER=groq
  AI_BASE_URL=https://api.groq.com/openai/v1
  AI_MODEL=llama-3.1-70b-versatile
  ```

Дополнительные опции см. ниже в разделе «Переменные окружения».

### 4. Запуск бота локально

```bash
.venv\Scripts\activate
python -m app.bot
```

После старта бот будет слушать обновления через long polling. Открой Telegram и напиши своему боту команду `/start`.

---

## Docker

### Сборка и запуск контейнера

```bash
docker build -t tg-ai-bot .
docker run --env-file .env --name tg-ai-bot --restart unless-stopped tg-ai-bot
```

- `--env-file .env` — пробрасывает все переменные окружения внутрь контейнера
- `--restart unless-stopped` — бот автоматически перезапускается при рестарте сервера

---

## Переменные окружения

Основные:

- **`TELEGRAM_BOT_TOKEN`** — токен бота от BotFather (**обязательно**)
- **`AI_PROVIDER`** — `openai` | `openrouter` | `groq`
- **`AI_API_KEY`** — API‑ключ AI‑провайдера (**обязательно**)
- **`AI_MODEL`** — имя модели (например, `gpt-4o-mini`, `openrouter/auto`, `llama-3.1-70b-versatile`)
- **`AI_BASE_URL`** — базовый URL Chat Completions API

Настройки логики бота:

- **`SYSTEM_PROMPT`** — системный промпт для ассистента (по умолчанию: `You are a helpful assistant.`)
- **`MAX_HISTORY_MESSAGES`** — размер истории сообщений на пользователя (по умолчанию: `8`)
- **`RATE_LIMIT_PER_MINUTE`** — лимит сообщений в минуту на пользователя (по умолчанию: `20`)

---

## Архитектура и ключевые компоненты

- **`app/bot.py`**
  - Инициализация `Bot` и `Dispatcher`
  - Регистрация хендлеров команд (`/start`, `/help`, `/clear`, `/templates`)
  - Основной обработчик входящих сообщений и callback‑ов
  - Логика выбора шаблонов и клавиатур

- **`app/ai_client.py`**
  - Обёртка над AI API (OpenAI / OpenRouter / Groq)
  - Метод `chat(messages)` для вызова `/chat/completions`

- **`app/memory.py`**
  - Класс `ConversationMemory` — хранение последних N сообщений на пользователя (in‑memory)

- **`app/rate_limiter.py`**
  - Класс `RateLimiter` — ограничение количества запросов в минуту на пользователя

- **`app/config.py`**
  - Класс `Settings` на базе `BaseSettings`
  - Чтение конфигурации из `.env`

- **`app/logger.py`**
  - Настройка базового логирования (`INFO`‑уровень, формат сообщений)

---

## Заметки по разработке

- История диалога и лимиты запросов хранятся в памяти процесса:
  - это упрощает запуск, но при рестарте бота история очищается;
  - для продакшена можно заменить на Redis/БД.
- Бот использует OpenAI‑совместимое Chat Completions API:
  - легко переключаться между провайдерами, если они поддерживают этот протокол.
- Не коммить файл `.env` в репозиторий:
  - API‑ключи и токены бота — **секретные данные**.

---

Если нужно, README легко адаптировать под конкретный хостинг/деплой (Docker, PaaS, bare metal и т.п.).
