import pytest
import uuid
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from jose import jwt

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    verify_token,
    blacklist_token,
    is_token_blacklisted,
    create_refresh_token,
    verify_refresh_token,
    revoke_refresh_token
)
from app.core.config import settings


# パスワード関連のテスト
def test_password_hash():
    """パスワードハッシュ化のテスト"""
    password = "testpassword123"
    hashed = get_password_hash(password)
    
    # ハッシュ化されたパスワードは元のパスワードと異なるはず
    assert hashed != password
    
    # 同じパスワードでも毎回異なるハッシュ値が生成されるはず
    hashed2 = get_password_hash(password)
    assert hashed != hashed2


def test_verify_password():
    """パスワード検証のテスト"""
    password = "testpassword123"
    wrong_password = "wrongpassword"
    hashed = get_password_hash(password)
    
    # 正しいパスワードは検証に成功するはず
    assert verify_password(password, hashed) is True
    
    # 誤ったパスワードは検証に失敗するはず
    assert verify_password(wrong_password, hashed) is False


# アクセストークン関連のテスト
@pytest.mark.asyncio
async def test_create_access_token():
    """アクセストークン生成のテスト"""
    user_id = "test_user_id"
    data = {"sub": user_id}
    
    # デフォルトの有効期限でトークンを生成
    token = await create_access_token(data)
    
    # トークンが文字列であることを確認
    assert isinstance(token, str)
    
    # トークンをデコードして内容を確認
    payload = jwt.decode(token, settings.PUBLIC_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == user_id
    assert "jti" in payload  # JTI（一意のトークンID）が含まれていることを確認
    assert "exp" in payload  # 有効期限が含まれていることを確認
    
    # カスタム有効期限でトークンを生成
    custom_expires = timedelta(minutes=5)
    token_custom = await create_access_token(data, expires_delta=custom_expires)
    
    # カスタム有効期限が正しく設定されていることを確認
    payload_custom = jwt.decode(token_custom, settings.PUBLIC_KEY, algorithms=[settings.ALGORITHM])
    
    # 有効期限が現在時刻から約5分後に設定されていることを確認（誤差を許容）
    exp_time = datetime.fromtimestamp(payload_custom["exp"], UTC)
    expected_exp = datetime.now(UTC) + custom_expires
    assert abs((exp_time - expected_exp).total_seconds()) < 10  # 10秒以内の誤差を許容


@pytest.mark.asyncio
async def test_verify_token():
    """トークン検証のテスト"""
    user_id = "test_user_id"
    data = {"sub": user_id}
    
    # 有効なトークンを生成
    token = await create_access_token(data)
    
    # is_token_blacklistedをモック
    with patch("app.core.security.is_token_blacklisted", return_value=False):
        # トークン検証が成功するはず
        payload = await verify_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
    
    # 不正なトークンの検証
    invalid_token = "invalid.token.string"
    payload_invalid = await verify_token(invalid_token)
    assert payload_invalid is None


@pytest.mark.asyncio
async def test_verify_token_blacklisted():
    """ブラックリストに登録されたトークンの検証テスト"""
    user_id = "test_user_id"
    data = {"sub": user_id}
    
    # 有効なトークンを生成
    token = await create_access_token(data)
    
    # is_token_blacklistedをモック（トークンがブラックリストに登録されている状態）
    with patch("app.core.security.is_token_blacklisted", return_value=True):
        # ブラックリストに登録されたトークンの検証は失敗するはず
        payload = await verify_token(token)
        assert payload is None


@pytest.mark.asyncio
async def test_blacklist_token():
    """トークンのブラックリスト登録テスト"""
    user_id = "test_user_id"
    data = {"sub": user_id}
    
    # 有効なトークンを生成
    token = await create_access_token(data)
    
    # Redisクライアントをモック
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.aclose = AsyncMock()
    
    # redis.from_urlをモック
    with patch("redis.asyncio.from_url", return_value=redis_mock):
        # トークンをブラックリストに登録
        result = await blacklist_token(token)
        assert result is True
        
        # Redisのsetexが呼び出されたことを確認
        redis_mock.setex.assert_called_once()
        # acloseが呼び出されたことを確認
        redis_mock.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_blacklist_token_disabled():
    """ブラックリスト機能が無効の場合のテスト"""
    # TOKEN_BLACKLIST_ENABLEDをモック（無効に設定）
    with patch("app.core.security.settings.TOKEN_BLACKLIST_ENABLED", False):
        # ブラックリスト機能が無効の場合は常にTrueを返すはず
        result = await blacklist_token("dummy_token")
        assert result is True


@pytest.mark.asyncio
async def test_blacklist_token_invalid():
    """無効なトークンのブラックリスト登録テスト"""
    # 無効なトークン
    invalid_token = "invalid.token.string"
    
    # 無効なトークンのブラックリスト登録は失敗するはず
    result = await blacklist_token(invalid_token)
    assert result is False


@pytest.mark.asyncio
async def test_is_token_blacklisted():
    """トークンのブラックリストチェックテスト"""
    # テスト用のペイロード
    jti = str(uuid.uuid4())
    payload = {"jti": jti}
    
    # Redisクライアントをモック
    redis_mock = AsyncMock()
    # ブラックリストに登録されている場合
    redis_mock.get = AsyncMock(return_value=b"1")
    redis_mock.aclose = AsyncMock()
    
    # redis.from_urlをモック
    with patch("redis.asyncio.from_url", return_value=redis_mock):
        # トークンがブラックリストに登録されているか確認
        result = await is_token_blacklisted(payload)
        assert result is True
        
        # Redisのgetが呼び出されたことを確認
        redis_mock.get.assert_called_once_with(f"blacklist_token:{jti}")
        # acloseが呼び出されたことを確認
        redis_mock.aclose.assert_called_once()
    
    # ブラックリストに登録されていない場合
    redis_mock.get = AsyncMock(return_value=None)
    
    with patch("redis.asyncio.from_url", return_value=redis_mock):
        # トークンがブラックリストに登録されていないことを確認
        result = await is_token_blacklisted(payload)
        assert result is False


@pytest.mark.asyncio
async def test_is_token_blacklisted_disabled():
    """ブラックリスト機能が無効の場合のブラックリストチェックテスト"""
    # テスト用のペイロード
    payload = {"jti": str(uuid.uuid4())}
    
    # TOKEN_BLACKLIST_ENABLEDをモック（無効に設定）
    with patch("app.core.security.settings.TOKEN_BLACKLIST_ENABLED", False):
        # ブラックリスト機能が無効の場合は常にFalseを返すはず
        result = await is_token_blacklisted(payload)
        assert result is False


@pytest.mark.asyncio
async def test_is_token_blacklisted_no_jti():
    """JTIがないペイロードのブラックリストチェックテスト"""
    # JTIがないペイロード
    payload = {"sub": "test_user_id"}
    
    # JTIがない場合は常にFalseを返すはず
    result = await is_token_blacklisted(payload)
    assert result is False


# リフレッシュトークン関連のテスト
@pytest.mark.asyncio
async def test_create_refresh_token():
    """リフレッシュトークン生成のテスト"""
    user_id = "test_user_id"
    
    # Redisクライアントをモック
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.aclose = AsyncMock()
    
    # redis.from_urlをモック
    with patch("redis.asyncio.from_url", return_value=redis_mock):
        # リフレッシュトークンを生成
        token = await create_refresh_token(user_id)
        
        # トークンが文字列であることを確認
        assert isinstance(token, str)
        # トークンの長さが十分であることを確認
        assert len(token) > 32
        
        # Redisのsetexが呼び出されたことを確認
        redis_mock.setex.assert_called_once()
        # 第1引数がトークンのキーであることを確認
        assert redis_mock.setex.call_args[0][0].startswith("refresh_token:")
        # 第2引数が有効期限（日数を秒に変換）であることを確認
        assert redis_mock.setex.call_args[0][1] == settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        # 第3引数がJSON文字列であることを確認
        import json
        token_data = json.loads(redis_mock.setex.call_args[0][2])
        assert token_data["auth_user_id"] == user_id
        assert "expires_at" in token_data
        
        # acloseが呼び出されたことを確認
        redis_mock.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_verify_refresh_token():
    """リフレッシュトークン検証のテスト"""
    user_id = "test_user_id"
    token = "test_refresh_token"
    
    # 現在時刻から1時間後のタイムスタンプ（有効期限）
    import time
    future_timestamp = int(time.time()) + 3600
    
    # トークンデータをJSON形式でエンコード
    import json
    token_data = {
        "auth_user_id": user_id,
        "expires_at": future_timestamp
    }
    token_data_encoded = json.dumps(token_data).encode()
    
    # Redisクライアントをモック
    redis_mock = AsyncMock()
    # 有効なトークンの場合
    redis_mock.get = AsyncMock(return_value=token_data_encoded)
    redis_mock.aclose = AsyncMock()
    
    # redis.from_urlをモック
    with patch("redis.asyncio.from_url", return_value=redis_mock):
        # リフレッシュトークンを検証
        result = await verify_refresh_token(token)
        
        # 結果がユーザーIDであることを確認
        assert result == user_id
        
        # Redisのgetが呼び出されたことを確認
        redis_mock.get.assert_called_once_with(f"refresh_token:{token}")
        # acloseが呼び出されたことを確認
        redis_mock.aclose.assert_called_once()
    
    # 無効なトークンの場合
    redis_mock.get = AsyncMock(return_value=None)
    
    with patch("redis.asyncio.from_url", return_value=redis_mock):
        # 無効なリフレッシュトークンの検証
        result = await verify_refresh_token(token)
        
        # 結果がNoneであることを確認
        assert result is None
        
    # 有効期限切れのトークンの場合
    expired_timestamp = int(time.time()) - 3600  # 1時間前
    expired_token_data = {
        "user_id": user_id,
        "expires_at": expired_timestamp
    }
    expired_token_data_encoded = json.dumps(expired_token_data).encode()
    
    redis_mock.get = AsyncMock(return_value=expired_token_data_encoded)
    
    # JWTErrorを発生させるためにrevoke_refresh_tokenをモック
    with patch("app.core.security.revoke_refresh_token", return_value=True):
        with patch("redis.asyncio.from_url", return_value=redis_mock):
            # 有効期限切れのトークンでJWTErrorが発生することを確認
            with pytest.raises(jwt.JWTError):
                await verify_refresh_token(token)


@pytest.mark.asyncio
async def test_revoke_refresh_token():
    """リフレッシュトークン無効化のテスト"""
    token = "test_refresh_token"
    
    # Redisクライアントをモック
    redis_mock = AsyncMock()
    # 正常に削除された場合
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.aclose = AsyncMock()
    
    # redis.from_urlをモック
    with patch("redis.asyncio.from_url", return_value=redis_mock):
        # リフレッシュトークンを無効化
        result = await revoke_refresh_token(token)
        
        # 結果がTrueであることを確認
        assert result is True
        
        # Redisのdeleteが呼び出されたことを確認
        redis_mock.delete.assert_called_once_with(f"refresh_token:{token}")
        # acloseが呼び出されたことを確認
        redis_mock.aclose.assert_called_once()
    
    # 削除対象が存在しない場合
    redis_mock.delete = AsyncMock(return_value=0)
    
    with patch("redis.asyncio.from_url", return_value=redis_mock):
        # 存在しないリフレッシュトークンの無効化
        result = await revoke_refresh_token(token)
        
        # 結果がFalseであることを確認
        assert result is False
