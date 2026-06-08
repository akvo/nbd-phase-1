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
    whatsapp_gcs_bucket: str = Field(...)

    @property
    def app_secret(self) -> str:
        return self.whatsapp_app_secret

    @property
    def verify_token(self) -> str:
        return self.whatsapp_verify_token

    @property
    def gcs_bucket(self) -> str:
        return self.whatsapp_gcs_bucket


def get_whatsapp_config() -> WhatsAppConfig:
    return WhatsAppConfig()
