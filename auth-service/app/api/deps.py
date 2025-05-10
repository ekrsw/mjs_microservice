from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from typing import Optional
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token, verify_refresh_token
from app.crud.auth_user import auth_user_crud
from app.db.session import get_async_session
from app.models.auth_user import AuthUser


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        async_session: AsyncSession = Depends(get_async_session)
        ) -> AuthUser:
    """
    アクセストークンからユーザーを取得する依存関数
    
    Args:
        token: JWTアクセストークン
        db: データベースセッション
        
    Returns:
        AuthUser: 認証されたユーザー
        
    Raises:
        HTTPException: トークンが無効な場合
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報が無効です",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = await verify_token(token)
        if payload is None:
            raise credentials_exception
        
        user_id: str = payload.get("user_id")
        
        if user_id is None:
            raise credentials_exception
    
    except (JWTError, ValidationError):
        raise credentials_exception
    
    # ユーザーをデータベースから取得
    user = await auth_user_crud.get_by_user_id(async_session, user_id)
    if user is None:
        raise credentials_exception
    
    return user

async def validate_refresh_token(refresh_token: str) -> Optional[str]:
    """
    リフレッシュトークンを検証する関数
    
    Args:
        refresh_token: 検証するリフレッシュトークン
        
    Returns:
        Optional[str]: トークンが有効な場合はユーザーID、無効な場合はNone
        
    Raises:
        HTTPException: トークンが無効な場合
    """
    user_id = await verify_refresh_token(refresh_token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="リフレッシュトークンが無効です",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user_id