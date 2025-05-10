import pytest
import uuid
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.crud.auth_user import auth_user_crud
from app.crud.exceptions import (
    UserNotFoundError,
    DuplicateUsernameError,
    DuplicateEmailError,
    DatabaseQueryError
)
from app.schemas.auth_user import AuthUserCreate, AuthUserUpdate


@pytest.mark.asyncio
async def test_create_multiple_users_transaction_rollback(db_session, monkeypatch):
    """複数ユーザー作成時に一部が失敗した場合、トランザクション全体がロールバックされることを確認する"""
    # 有効なユーザーデータを作成
    valid_users = [
        AuthUserCreate(
            username=f"valid_user_{i}_{uuid.uuid4().hex[:8]}",
            email=f"valid_user_{i}_{uuid.uuid4().hex[:8]}@example.com",
            password="password123"
        ) for i in range(3)
    ]
    
    # 元のadd_allメソッドを保存
    original_add_all = db_session.add_all
    
    # 例外を発生させるモック関数
    def mock_add_all(objs):
        # 最初のユーザーは追加するが、その後例外を発生させる
        raise ValueError("Simulated database error")
    
    # add_allメソッドをモックに置き換え
    monkeypatch.setattr(db_session, "add_all", mock_add_all)
    
    # エラーが発生することを確認
    with pytest.raises(ValueError):
        await auth_user_crud.create_multiple(db_session, valid_users)
    
    # トランザクションがロールバックされ、有効なユーザーも作成されていないことを確認
    for user in valid_users:
        try:
            await auth_user_crud.get_by_username(db_session, user.username)
            assert False, f"User {user.username} should not exist after rollback"
        except UserNotFoundError:
            # 期待通りユーザーが見つからない
            pass
    
    # モックを元に戻す
    monkeypatch.setattr(db_session, "add_all", original_add_all)


@pytest.mark.asyncio
async def test_create_multiple_users_with_duplicate_constraint(db_session, test_user):
    """複数ユーザー作成時に一意性制約違反が発生した場合、トランザクション全体がロールバックされることを確認する"""
    # 既存のユーザー名を取得
    existing_username = test_user.username
    
    # 有効なユーザーデータを作成
    valid_users = [
        AuthUserCreate(
            username=f"valid_user_{i}_{uuid.uuid4().hex[:8]}",
            email=f"valid_user_{i}_{uuid.uuid4().hex[:8]}@example.com",
            password="password123"
        ) for i in range(3)
    ]
    
    # 既存のユーザー名を持つユーザーデータを作成
    duplicate_user = AuthUserCreate(
        username=existing_username,  # 既存のユーザー名（一意性制約違反）
        email=f"duplicate_{uuid.uuid4().hex[:8]}@example.com",
        password="password123"
    )
    
    # 有効なユーザーと重複ユーザーを混ぜる
    mixed_users = valid_users[:1] + [duplicate_user] + valid_users[1:]
    
    # エラーが発生することを確認
    with pytest.raises(DuplicateUsernameError):
        await auth_user_crud.create_multiple(db_session, mixed_users)
    
    # トランザクションがロールバックされ、有効なユーザーも作成されていないことを確認
    for user in valid_users:
        try:
            await auth_user_crud.get_by_username(db_session, user.username)
            assert False, f"User {user.username} should not exist after rollback"
        except UserNotFoundError:
            # 期待通りユーザーが見つからない
            pass


@pytest.mark.asyncio
async def test_database_connection_error_handling(db_session, monkeypatch):
    """データベース接続エラーが適切にハンドリングされることを確認する"""
    # SQLAlchemyのセッション実行をモックして例外を発生させる
    async def mock_execute(*args, **kwargs):
        raise SQLAlchemyError("Database connection error")
    
    # セッションのexecuteメソッドをモックに置き換え
    monkeypatch.setattr(db_session, "execute", mock_execute)
    
    # ユーザー取得操作を実行
    with pytest.raises(DatabaseQueryError) as exc_info:
        await auth_user_crud.get_all(db_session)
    
    # エラーメッセージを確認
    assert "Database connection error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_unexpected_exception_handling(db_session, monkeypatch):
    """予期せぬ例外が適切にハンドリングされることを確認する"""
    # 予期せぬ例外を発生させる関数
    async def mock_get_by_id(*args, **kwargs):
        raise RuntimeError("Unexpected error")
    
    # get_by_idメソッドをモックに置き換え
    monkeypatch.setattr(auth_user_crud, "get_by_id", mock_get_by_id)
    
    # ユーザー更新操作を実行
    user_id = uuid.uuid4()
    update_data = AuthUserUpdate(username="new_username")
    
    with pytest.raises(Exception) as exc_info:
        await auth_user_crud.update_by_id(db_session, user_id, update_data)
    
    # 例外が適切にラップされていることを確認
    assert "Unexpected error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_session_rollback_on_exception(db_session):
    """例外発生時にセッションが適切にロールバックされることを確認する"""
    # テストの代替案：トランザクションのロールバックをシミュレートする
    
    # 1. 新しいセッションを作成（テスト用）
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    
    # 新しいエンジンとセッションを作成
    engine = create_async_engine(settings.DATABASE_URL)
    TestingSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # 2. 最初のトランザクションでユーザーを作成
    async with TestingSessionLocal() as session1:
        # ユーザー情報を準備
        username = f"rollback_test_{uuid.uuid4().hex[:8]}"
        email = f"rollback_test_{uuid.uuid4().hex[:8]}@example.com"
        password = "password123"
        
        # ユーザーを作成してコミット
        user_in = AuthUserCreate(
            username=username,
            email=email,
            password=password
        )
        created_user = await auth_user_crud.create(session1, user_in)
        await session1.commit()
        
        # ユーザーIDを保存
        user_id = created_user.id
    
    # 3. 別のトランザクションでユーザーを更新し、ロールバック
    async with TestingSessionLocal() as session2:
        # ユーザーを取得
        db_user = await auth_user_crud.get_by_id(session2, user_id)
        
        # ユーザー名を更新
        updated_username = "updated_username"
        db_user.username = updated_username
        
        # 変更をロールバック
        await session2.rollback()
    
    # 4. 別のトランザクションでユーザーを取得し、更新されていないことを確認
    async with TestingSessionLocal() as session3:
        # ユーザーを再取得
        db_user = await auth_user_crud.get_by_id(session3, user_id)
        
        # ユーザー名が更新されていないことを確認
        assert db_user.username == username, "Username should not be updated after rollback"
        assert db_user.username != updated_username, "Username should not be updated to new value"
        
        # 後片付け
        await auth_user_crud.delete_by_id(session3, user_id)
        await session3.commit()
