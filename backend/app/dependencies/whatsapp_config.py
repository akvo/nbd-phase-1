"""WhatsApp Meta Cloud API dependency settings.

All pipelines share a single GCS bucket (GCS_BUCKET_NAME). The previous
WHATSAPP_GCS_BUCKET env var has been removed in favour of the unified
bucket + path-prefix strategy (FR-001).
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WhatsAppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Field names must match env var names (case-insensitive)
    whatsapp_app_secret: str = Field(...)
    whatsapp_verify_token: str = Field(...)

    @property
    def app_secret(self) -> str:
        return self.whatsapp_app_secret

    @property
    def verify_token(self) -> str:
        return self.whatsapp_verify_token


def get_whatsapp_config() -> WhatsAppConfig:
    return WhatsAppConfig()
