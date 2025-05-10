from typing import Optional
import uuid
from pydantic import BaseModel, EmailStr, Field


class AuthUserBase(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None


class AuthUserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=16)


class AuthUserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    user_id: Optional[uuid.UUID] = None
    # passowrdは更新しない


class AuthUserUpdatePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=1, max_length=16)


# レスポンスとして返すユーザー情報
class AuthUserInDBBase(AuthUserBase):
    id: uuid.UUID
    username: str
    email: EmailStr
    user_id: Optional[uuid.UUID] = None

    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True
    }


class AuthUserResponse(AuthUserInDBBase):
    pass


# トークン関連のスキーマ
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None


# リフレッシュトークンリクエスト用のスキーマ（access_tokenを必須とする）
class RefreshTokenRequest(BaseModel):
    refresh_token: str
    access_token: str


# ログアウトリクエスト用のスキーマ（access_tokenを必須とする）
class LogoutRequest(BaseModel):
    refresh_token: str
    access_token: str