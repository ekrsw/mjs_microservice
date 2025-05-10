import os
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional, Literal


class Settings(BaseSettings):
    # 環境設定
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"

    # ロギング設定
    LOG_LEVEL: str = "INFO"
    LOG_TO_FILE: bool = False
    LOG_FILE_PATH: str = "logs/USER_service.log"
    
    # RabbitMQ設定
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_RETRY_COUNT: int = 5

     # データベース関係
    USER_POSTGRES_HOST: str
    USER_POSTGRES_INTERNAL_PORT: str = "5432"
    USER_POSTGRES_USER: str
    USER_POSTGRES_PASSWORD: str
    USER_POSTGRES_DB: str
    TZ: str

    # トークン設定
    ALGORITHM: str = "RS256"
    PUBLIC_KEY_PATH: str = "keys/public.pem"   # 公開鍵のパス

    # SQLAlchemyのログ出力設定
    SQLALCHEMY_ECHO: bool = True

    # 外部接続用ポート
    USER_POSTGRES_EXTERNAL_PORT: str

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.USER_POSTGRES_USER}:{self.USER_POSTGRES_PASSWORD}@"
            f"{self.USER_POSTGRES_HOST}:{self.USER_POSTGRES_INTERNAL_PORT}/"
            f"{self.USER_POSTGRES_DB}"
        )
    
    @property
    def PUBLIC_KEY(self) -> str:
        """公開鍵の内容を読み込む"""
        try:
            with open(self.PUBLIC_KEY_PATH, "r") as f:
                return f.read()
        except FileNotFoundError:
            return os.environ.get("PUBLIC_KEY", "")
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

settings = Settings()
