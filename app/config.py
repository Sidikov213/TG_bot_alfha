import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ai_provider: str = os.getenv("AI_PROVIDER", "openai")
    ai_api_key: str = os.getenv("AI_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "gpt-4o-mini")
    ai_base_url: str = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
    system_prompt: str = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")
    max_history_messages: int = int(os.getenv("MAX_HISTORY_MESSAGES", "8"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
    admin_user_id: int | None = (
        int(os.getenv("ADMIN_USER_ID")) if os.getenv("ADMIN_USER_ID") else None
    )

settings = Settings()
