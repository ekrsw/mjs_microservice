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
    LOG_FILE_PATH: str = "logs/auth_service.log"

    # RabbitMQ設定
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    USER_SYNC_EXCHANGE: str = "user_events"
    USER_SYNC_ROUTING_KEY: str = "user.sync"

    # データベース関係
    AUTH_POSTGRES_HOST: str
    AUTH_POSTGRES_INTERNAL_PORT: str = "5432"
    AUTH_POSTGRES_USER: str
    AUTH_POSTGRES_PASSWORD: str
    AUTH_POSTGRES_DB: str
    TZ: str

    # Redis設定
    AUTH_REDIS_HOST: str = "auth_redis"
    AUTH_REDIS_PORT: str = "6379"
    AUTH_REDIS_PASSWORD: Optional[str] = None

    # トークン設定
    ALGORITHM: str = "RS256"
    PRIVATE_KEY_PATH: str = "keys/private.pem"  # 秘密鍵のパス
    PUBLIC_KEY_PATH: str = "keys/public.pem"   # 公開鍵のパス
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # トークンブラックリスト関連の設定
    TOKEN_BLACKLIST_ENABLED: bool = True

    # SQLAlchemyのログ出力設定
    SQLALCHEMY_ECHO: bool = True

    # 外部接続用ポート
    AUTH_POSTGRES_EXTERNAL_PORT: str
    AUTH_REDIS_EXTERNAL_PORT: str

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.AUTH_POSTGRES_USER}:{self.AUTH_POSTGRES_PASSWORD}@"
            f"{self.AUTH_POSTGRES_HOST}:{self.AUTH_POSTGRES_INTERNAL_PORT}/"
            f"{self.AUTH_POSTGRES_DB}"
        )
    
    @property
    def AUTH_REDIS_URL(self) -> str:
        if self.AUTH_REDIS_PASSWORD:
            return f"redis://:{self.AUTH_REDIS_PASSWORD}@{self.AUTH_REDIS_HOST}:{self.AUTH_REDIS_PORT}/0"
        return f"redis://{self.AUTH_REDIS_HOST}:{self.AUTH_REDIS_PORT}/0"
    
    @property
    def PRIVATE_KEY(self) -> str:
        """秘密鍵の内容を読み込む"""
        try:
            with open(self.PRIVATE_KEY_PATH, "r") as f:
                return f.read()
        except FileNotFoundError:
            # 開発環境では環境変数から直接読み込む選択肢も
            return os.environ.get("PRIVATE_KEY", "")
    
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
