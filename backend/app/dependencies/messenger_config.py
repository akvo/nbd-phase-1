from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from typing import Optional


class MessengerConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    messenger_app_secret: str = Field(
        default="mock_messenger_secret",
        description="Meta App Secret for HMAC-SHA256 signature verification",
    )
    messenger_verify_token: str = Field(
        default="nbd_messenger_verify_token",
        description="Webhook GET challenge verification token",
    )
    messenger_page_token: str = Field(
        default="mock_page_token",
        description="Meta Graph API Page Access Token",
    )
    messenger_page_id: Optional[str] = Field(
        default="NBD_PAGE_1001",
        description="Primary Facebook Page ID for NBD",
    )


@lru_cache()
def get_messenger_config() -> MessengerConfig:
    return MessengerConfig()
