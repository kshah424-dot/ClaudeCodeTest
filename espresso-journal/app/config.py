from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    confluence_base_url: str = ""
    confluence_email: str = ""
    confluence_api_token: str = ""
    confluence_space_key: str = ""
    confluence_parent_page_id: str | None = None

    host: str = "0.0.0.0"
    port: int = 8000
    webhook_secret: str | None = None


settings = Settings()
