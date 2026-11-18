from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    # Bắt buộc, KHÔNG có giá trị mặc định: thiếu thì ứng dụng không khởi động
    JWT_SECRET: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    STORAGE_DIR: str = "storage"   # nơi lưu ảnh sự cố (Docker: mount volume vào đây)
    MAX_UPLOAD_MB: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
