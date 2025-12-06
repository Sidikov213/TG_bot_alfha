from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    backend_url: str = Field(default="http://localhost:3000", alias="BACKEND_URL")
    # Старые настройки AI (оставлены для обратной совместимости, но не используются)
    ai_provider: str = Field(default="openai", alias="AI_PROVIDER")
    ai_api_key: str = Field(default="", alias="AI_API_KEY")
    ai_model: str = Field(default="gpt-4o-mini", alias="AI_MODEL")
    ai_base_url: str = Field(default="https://api.openai.com/v1", alias="AI_BASE_URL")
    system_prompt: str = Field(default="You are a helpful assistant.", alias="SYSTEM_PROMPT")
    max_history_messages: int = Field(default=8, alias="MAX_HISTORY_MESSAGES")
    rate_limit_per_minute: int = Field(default=20, alias="RATE_LIMIT_PER_MINUTE")
    admin_user_id: Optional[int] = Field(default=None, alias="ADMIN_USER_ID")

settings = Settings()
