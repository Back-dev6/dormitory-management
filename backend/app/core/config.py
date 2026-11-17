from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    STORAGE_DIR: str = "storage"   # nơi lưu ảnh sự cố (Docker: mount volume vào đây)
    MAX_UPLOAD_MB: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
