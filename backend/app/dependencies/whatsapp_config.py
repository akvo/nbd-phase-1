"""WhatsApp Twilio API dependency settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WhatsAppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Field names must match env var names (case-insensitive)
    twilio_account_sid: str = Field(...)
    twilio_auth_token: str = Field(...)
    twilio_number: str = Field(...)

    @property
    def account_sid(self) -> str:
        return self.twilio_account_sid

    @property
    def auth_token(self) -> str:
        return self.twilio_auth_token

    @property
    def from_number(self) -> str:
        return self.twilio_number


def get_whatsapp_config() -> WhatsAppConfig:
    return WhatsAppConfig()
