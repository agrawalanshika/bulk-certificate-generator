from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bulk Certificate Generator"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    database_url: str = "sqlite:///./certificates.db"
    generated_dir: str = "generated"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()