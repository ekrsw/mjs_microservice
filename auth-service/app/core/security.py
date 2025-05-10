from datetime import datetime, timedelta, UTC
import json
import secrets
from typing import Dict, Any, Optional
import uuid

from passlib.context import CryptContext
from jose import jwt, JWTError
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import app_logger


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:

    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    非対称暗号を使用してアクセストークンを作成する関数
    
    Args:
        data: トークンに含めるデータ（通常はユーザーID）
        expires_delta: トークンの有効期限（指定がない場合はデフォルト値を使用）
        
    Returns:
        str: 生成されたJWTトークン
    """
    to_encode = data.copy()
    jti = str(uuid.uuid4())
    to_encode.update({"jti": jti})
    
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # 秘密鍵を使用してトークンを署名
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.PRIVATE_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

# ブラックリストに追加する関数
async def blacklist_token(token: str) -> bool:
    """トークンをブラックリストに追加する"""
    # ブラックリスト機能が無効の場合は常にTrue（成功）を返す
    if not settings.TOKEN_BLACKLIST_ENABLED:
        return True
        
    try:
        # ここではブラックリストチェックを除外したトークン検証が必要
        # そうしないと無限ループになるので、直接JWTデコードする
        try:
            payload = jwt.decode(token,
                               settings.PUBLIC_KEY,
                               algorithms=[settings.ALGORITHM])
        except JWTError:
            return False
            
        if not payload:
            return False
            
        jti = payload.get("jti")
        if not jti:
            return False  # jtiがない場合は古いトークン形式
            
        exp = payload.get("exp")
        
        # 有効期限を計算
        now = datetime.now(UTC).timestamp()
        ttl = max(int(exp - now), 0)
        
        # Redisに保存
        r = redis.from_url(settings.AUTH_REDIS_URL)
        await r.setex(f"blacklist_token:{jti}", ttl, "1")
        await r.aclose()
        return True
    except Exception as e:
        app_logger.error(f"トークンのブラックリスト登録中にエラーが発生しました: {str(e)}", exc_info=True)
        return False

# ブラックリストチェック関数
async def is_token_blacklisted(payload: Dict[str, Any]) -> bool:
    """トークンがブラックリストに登録されているか確認"""
    # ブラックリスト機能が無効の場合は常にFalse（ブラックリストされていない）を返す
    if not settings.TOKEN_BLACKLIST_ENABLED:
        return False
        
    jti = payload.get("jti")
    if not jti:
        return False  # jtiがない場合は古いトークン形式なのでブラックリスト非対象
        
    r = redis.from_url(settings.AUTH_REDIS_URL)
    result = await r.get(f"blacklist_token:{jti}")
    await r.aclose()
    
    return result is not None

async def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    JWTトークンを検証し、ペイロードを返す関数
    
    Args:
        token: 検証するJWTトークン
        
    Returns:
        Optional[Dict[str, Any]]: トークンが有効な場合はペイロード、無効な場合はNone
    """
    try:
        # 公開鍵を使用してトークンを検証
        payload = jwt.decode(token,
                             settings.PUBLIC_KEY,
                             algorithms=[settings.ALGORITHM]
                             )
        
        # ブラックリストチェック
        if await is_token_blacklisted(payload):
            return None
        
        return payload
    except JWTError:
        return None

async def create_refresh_token(auth_user_id: str) -> str:
    """
    リフレッシュトークンを作成し、Redisに保存する関数
    
    Args:
        auth_user_id: ユーザーID
        
    Returns:
        str: 生成されたリフレッシュトークン
    """
    # ランダムなトークンを生成
    token = secrets.token_urlsafe(32)
    
    # 有効期限を計算
    expiry_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # 日数を秒に変換
    expiry_timestamp = int((datetime.now(UTC) + timedelta(seconds=expiry_seconds)).timestamp())
    
    # トークンデータをJSON形式で保存
    token_data = {
        "auth_user_id": auth_user_id,
        "expires_at": expiry_timestamp
    }
    
    # Redisクライアントを初期化
    r = redis.from_url(settings.AUTH_REDIS_URL)
    
    # トークンをRedisに保存（キー: トークン, 値: トークンデータのJSON）
    await r.setex(f"refresh_token:{token}", expiry_seconds, json.dumps(token_data))
    
    # 接続を閉じる
    await r.aclose()
    
    return token

async def verify_refresh_token(token: str) -> Optional[str]:
    """
    リフレッシュトークンを検証し、関連するユーザーIDを返す関数
    
    Args:
        token: 検証するリフレッシュトークン
        
    Returns:
        Optional[str]: トークンが有効な場合はユーザーID、無効な場合はNone
        
    Raises:
        JWTError: トークンの有効期限が切れている場合
    """
    # Redisクライアントを初期化
    r = redis.from_url(settings.AUTH_REDIS_URL)
    
    # トークンをRedisから取得
    token_data_str = await r.get(f"refresh_token:{token}")
    
    # 接続を閉じる
    await r.aclose()
    
    if not token_data_str:
        return None
    
    try:
        # JSONデータをパース
        token_data = json.loads(token_data_str)
        
        # 有効期限をチェック
        current_timestamp = datetime.now(UTC).timestamp()
        if token_data.get("expires_at", 0) < current_timestamp:
            app_logger.warning(f"リフレッシュトークンの有効期限切れ: {token}")
            # 期限切れのトークンを削除
            await revoke_refresh_token(token)
            raise jwt.JWTError("リフレッシュトークンの有効期限が切れています")
        
        return token_data.get("auth_user_id")
    except json.JSONDecodeError:
        app_logger.error(f"リフレッシュトークンのデータ形式が不正: {token_data_str}")
        return None

async def revoke_refresh_token(token: str) -> bool:
    """
    リフレッシュトークンを無効化する関数
    
    Args:
        token: 無効化するリフレッシュトークン
        
    Returns:
        bool: 無効化に成功した場合はTrue、失敗した場合はFalse
    """
    # Redisクライアントを初期化
    r = redis.from_url(settings.AUTH_REDIS_URL)
    
    # トークンをRedisから削除
    result = await r.delete(f"refresh_token:{token}")
    
    # 接続を閉じる
    await r.aclose()
    
    return result > 0