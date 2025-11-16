# Telegram AI Bot (aiogram)

Production-ready Telegram bot that answers with AI (OpenAI/OpenRouter/Groq). Built with aiogram v3, async HTTP, simple memory, and rate limiting.

## Features
- /start and /help
- Chat replies with conversation memory per user
- Pluggable AI provider via env
- Basic rate limiting
- Structured logging
- Docker support

## Quick start (Windows)
1) Python 3.11+
2) Create venv and install deps:
```
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```
3) Copy env template and edit:
```
copy env.example .env
```
Fill `TELEGRAM_BOT_TOKEN`, `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`.

OpenAI example:
```
AI_PROVIDER=openai
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```
OpenRouter example:
```
AI_PROVIDER=openrouter
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=openrouter/auto
```
Groq example:
```
AI_PROVIDER=groq
AI_BASE_URL=https://api.groq.com/openai/v1
AI_MODEL=llama-3.1-70b-versatile
```

4) Run the bot:
```
python -m app.bot
```

## Docker
Build and run:
```
docker build -t tg-ai-bot .
docker run --env-file .env --name tg-ai-bot --restart unless-stopped tg-ai-bot
```

## Environment variables
- TELEGRAM_BOT_TOKEN
- AI_PROVIDER: openai | openrouter | groq
- AI_API_KEY
- AI_MODEL
- AI_BASE_URL
- SYSTEM_PROMPT (optional)
- MAX_HISTORY_MESSAGES (default 8)
- RATE_LIMIT_PER_MINUTE (default 20)
- ADMIN_USER_ID (optional)

## Notes
- Keep your API keys safe. Do not commit `.env`.
- This bot uses OpenAI-compatible Chat Completions API.
