# Telegram AI Business Bot (aiogram)

AI-powered business assistant in Telegram that answers with OpenAI / OpenRouter / Groq models, keeps per-user conversation context, limits request rate, and provides ready-made templates for typical business tasks (finance, clients, contracts, operations).

The bot is written in Python using `aiogram v3`, async HTTP requests and simple in-memory storage for both dialog history and rate limiting.

---

## Features

- **Basic commands**
  - `/start` — greeting and short description of bot capabilities  
  - `/help` — list of available commands  
  - `/clear` — clear dialog history for the current user  
  - `/templates` or the "Templates" button — open a set of ready-made prompts  

- **AI chat**
  - Assistant replies using an AI model (OpenAI, OpenRouter or Groq via OpenAI-compatible Chat Completions API)
  - **Per-user dialog memory**: the bot keeps the last messages (up to `MAX_HISTORY_MESSAGES`)  
  - System prompt is configured via the `SYSTEM_PROMPT` environment variable

- **Business templates**
  - Categories:
    - Finance (estimate, invoice, payment plan, budget)
    - Clients (commercial offer, call script, email, objection handling)
    - Contracts (draft contract, refund policy, offer)
    - Operations (brief, internal regulations, promotion plan)
  - Ability to "insert" a template into the input field with a single tap

- **Rate limiting**
  - Simple in-memory rate limiter: up to `RATE_LIMIT_PER_MINUTE` messages per minute per user

- **Logging**
  - Structured logs for bot startup/shutdown and AI errors

- **Infrastructure**
  - Dockerfile for easy deployment
  - Configuration via `.env`

---

## Tech Stack

- **Language**: Python 3.11+
- **Telegram framework**: [aiogram v3](https://docs.aiogram.dev/)
- **AI client**: any provider with OpenAI-compatible Chat Completions API:
  - OpenAI (`https://api.openai.com/v1`)
  - OpenRouter (`https://openrouter.ai/api/v1`)
  - Groq (`https://api.groq.com/openai/v1`)
- **Configuration**: `pydantic-settings`
- **HTTP client**: `httpx` (async)
- **Logging**: standard Python `logging`
- **Dialog memory**: in-memory (dict + `deque`)
- **Rate limiting**: in-memory rate limiter

---

## Quick Start (Windows)

### 1. Requirements

- Installed **Python 3.11+**
- Installed **Git** (optional)
- Account and API key for your chosen AI provider
- Created Telegram bot and its token (via BotFather)

### 2. Clone and install dependencies

```bash
git clone https://github.com/Sidikov213/TG_bot_alfha.git
cd TG_bot_alfha

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment configuration

Copy the example env file:

```bash
copy env.example .env
```

Edit `.env` and fill in the key variables:

```env
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN

AI_PROVIDER=openai           # or openrouter / groq
AI_API_KEY=YOUR_API_KEY
AI_MODEL=gpt-4o-mini         # or another model of your provider
AI_BASE_URL=https://api.openai.com/v1
```

Configuration examples:

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

Additional options are described in the **Environment variables** section below.

### 4. Run the bot locally

```bash
.venv\Scripts\activate
python -m app.bot
```

After startup the bot will use long polling to receive updates. Open Telegram and send `/start` to your bot.

---

## Docker

### Build and run container

```bash
docker build -t tg-ai-bot .
docker run --env-file .env --name tg-ai-bot --restart unless-stopped tg-ai-bot
```

- `--env-file .env` — passes all environment variables into the container
- `--restart unless-stopped` — automatically restarts the bot when the server restarts

---

## Environment variables

Main variables:

- **`TELEGRAM_BOT_TOKEN`** — bot token from BotFather (**required**)
- **`AI_PROVIDER`** — `openai` | `openrouter` | `groq`
- **`AI_API_KEY`** — AI provider API key (**required**)
- **`AI_MODEL`** — model name (e.g. `gpt-4o-mini`, `openrouter/auto`, `llama-3.1-70b-versatile`)
- **`AI_BASE_URL`** — base URL of Chat Completions API

Bot behavior settings:

- **`SYSTEM_PROMPT`** — system prompt for the assistant (default: `You are a helpful assistant.`)
- **`MAX_HISTORY_MESSAGES`** — number of messages kept per user (default: `8`)
- **`RATE_LIMIT_PER_MINUTE`** — messages per minute limit per user (default: `20`)

---

## Architecture and key components

- **`app/bot.py`**
  - Initializes `Bot` and `Dispatcher`
  - Registers command handlers (`/start`, `/help`, `/clear`, `/templates`)
  - Main handler for incoming messages and callback queries
  - Business templates and keyboard logic

- **`app/ai_client.py`**
  - Wrapper around AI APIs (OpenAI / OpenRouter / Groq)
  - `chat(messages)` method for calling `/chat/completions`

- **`app/memory.py`**
  - `ConversationMemory` class — stores last N messages per user (in-memory)

- **`app/rate_limiter.py`**
  - `RateLimiter` class — per-user messages-per-minute limiting

- **`app/config.py`**
  - `Settings` class based on `BaseSettings`
  - Reads configuration from `.env`

- **`app/logger.py`**
  - Basic logging setup (`INFO` level, message format)

---

## Development notes

- Dialog history and rate-limiting data are stored in process memory:
  - this makes the bot easy to run locally, but history is lost after restart;
  - for production you can replace this with Redis/DB.
- The bot uses an OpenAI-compatible Chat Completions API:
  - easy to switch between providers as long as they support this protocol.
- Do **not** commit `.env` to the repository:
  - API keys and bot tokens are **sensitive credentials**.

---

This README describes the English version of the project. The main `README.ru.md` contains a Russian version tailored for Russian-speaking users and hackathon context.
