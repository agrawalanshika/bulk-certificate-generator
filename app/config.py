from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bulk Certificate Generator"
    app_version: str = "0.1.0"
    debug: bool = False
    database_url: str = "sqlite:///./certificates.db"
    generated_dir: str = "generated"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
