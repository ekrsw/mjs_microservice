import time
from redis.asyncio import Redis
from typing import Optional

from app.core.config import settings
from app.core.logging import app_logger

# Redis接続プール
_redis = None

async def get_redis_pool():
    """
    Redisプールを取得する。まだ接続されていない場合は接続を作成する。
    """
    global _redis
    if _redis is None:
        try:
            _redis = Redis.from_url(
                settings.AUTH_REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            app_logger.info(f"Redis接続プール作成: {settings.AUTH_REDIS_HOST}:{settings.AUTH_REDIS_PORT}")
        except Exception as e:
            app_logger.error(f"Redis接続エラー: {str(e)}", exc_info=True)
            raise
    return _redis

async def save_password_to_redis(username: str, password: str, ttl_seconds: int = 300) -> str:
    """
    パスワードをRedisに一時保存する
    
    Args:
        username: ユーザー名
        password: パスワード
        ttl_seconds: 有効期限（秒）、デフォルトは5分
        
    Returns:
        作成されたキー文字列
    """
    redis = await get_redis_pool()
    timestamp = int(time.time())
    key = f"temp_password:{username}:{timestamp}"
    
    try:
        # キーと共にパスワードを保存し、TTLを設定
        await redis.setex(key, ttl_seconds, password)
        app_logger.info(f"パスワードを一時保存しました: {key}, TTL={ttl_seconds}秒")
        return key
    except Exception as e:
        app_logger.error(f"パスワードの一時保存に失敗: {str(e)}", exc_info=True)
        raise

async def get_password_from_redis(key: str) -> Optional[str]:
    """
    Redisから一時保存されたパスワードを取得する
    
    Args:
        key: パスワードを保存するときに使用したキー
        
    Returns:
        パスワード文字列、キーが見つからない場合はNone
    """
    redis = await get_redis_pool()
    try:
        password = await redis.get(key)
        if password:
            app_logger.info(f"パスワードを取得しました: {key}")
            return password
        else:
            app_logger.warning(f"パスワードが見つかりません: {key}")
            return None
    except Exception as e:
        app_logger.error(f"パスワード取得エラー: {str(e)}", exc_info=True)
        return None

async def delete_password_from_redis(key: str) -> bool:
    """
    Redisから一時保存されたパスワードを削除する
    
    Args:
        key: パスワードを保存するときに使用したキー
        
    Returns:
        削除に成功した場合はTrue、失敗した場合はFalse
    """
    redis = await get_redis_pool()
    try:
        result = await redis.delete(key)
        if result:
            app_logger.info(f"パスワードを削除しました: {key}")
            return True
        else:
            app_logger.warning(f"パスワード削除失敗（既に存在しません）: {key}")
            return False
    except Exception as e:
        app_logger.error(f"パスワード削除エラー: {str(e)}", exc_info=True)
        return False
