from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import uuid


class UserCreateRequest(BaseModel):
    """auth-serviceからuser-serviceへのユーザー作成リクエスト"""
    # メッセージメタデータ
    message_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="メッセージの一意識別子")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="メッセージ作成時刻")
    
    # ユーザー基本情報
    username: str = Field(..., description="ユーザー名")
    email: EmailStr = Field(..., description="メールアドレス")
    
    # その他のメタデータ
    source_service: str = Field(default="auth-service", description="送信元サービス")
    retry_count: int = Field(default=0, description="リトライ回数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2025-05-06T03:00:00",
                "username": "testuser",
                "email": "user@example.com",
                "source_service": "auth-service",
                "retry_count": 0
            }
        }


class UserCreationStatus(str, Enum):
    """ユーザー作成結果のステータス"""
    SUCCESS = "success"
    DUPLICATE_USERNAME = "duplicate_username"
    DUPLICATE_EMAIL = "duplicate_email" 
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_ERROR = "unknown_error"


class UserCreatedResponse(BaseModel):
    """user-serviceからauth-serviceへのユーザー作成結果通知"""
    # メッセージメタデータ
    message_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="メッセージの一意識別子")
    request_id: uuid.UUID = Field(..., description="リクエストメッセージのID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="メッセージ作成時刻")
    
    # 処理結果
    status: UserCreationStatus = Field(..., description="処理結果ステータス")
    error_message: Optional[str] = Field(None, description="エラーメッセージ（失敗時）")
    
    # 作成されたユーザー情報
    user_id: Optional[uuid.UUID] = Field(None, description="作成されたユーザーID（成功時のみ）")
    username: str = Field(..., description="ユーザー名")
    email: EmailStr = Field(..., description="メールアドレス")
    
    # その他のメタデータ
    source_service: str = Field(default="user-service", description="送信元サービス")
    processing_time_ms: Optional[float] = Field(None, description="処理時間（ミリ秒）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "123e4567-e89b-12d3-a456-426614174001",
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2025-05-06T03:00:05",
                "status": "success",
                "error_message": None,
                "user_id": "123e4567-e89b-12d3-a456-426614174002",
                "username": "testuser",
                "email": "user@example.com",
                "source_service": "user-service",
                "processing_time_ms": 120.45
            }
        }
