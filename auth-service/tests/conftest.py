import pytest
import pytest_asyncio
import random
import string
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.crud.auth_user import auth_user_crud
from app.schemas.auth_user import AuthUserCreate

# テスト用のインメモリSQLiteデータベース
@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    AsyncSessionLocal = sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback() # 常にトランザクションをロールバックして状態を元に戻す
            await session.close()

@pytest.fixture(scope="function")
def unique_username():
    """ユニークなユーザー名を生成する"""
    return f"user_{uuid.uuid4()}"

@pytest.fixture(scope="function")
def unique_email():
    """ユニークなメールアドレスを生成する"""
    return f"user_{uuid.uuid4()}@example.com"

@pytest.fixture(scope="function")
def unique_password():
    """ユニークなパスワードを生成する"""
    # パスワードの長さをランダムに決定（1～16文字）
    length = random.randint(1, 16)
    
    # 使用する文字セット
    characters = string.ascii_letters + string.digits + string.punctuation
    
    # ランダムなパスワードを生成
    password = ''.join(random.choice(characters) for _ in range(length))
    
    return password

@pytest_asyncio.fixture(scope="function")
async def test_user(db_session, unique_username, unique_email):
    """テスト用のユーザーを作成する"""
    username = unique_username
    email = unique_email
    password = "password123"
    user_in = AuthUserCreate(username=username, email=email, password=password)
    db_user = await auth_user_crud.create(db_session, user_in)
    await db_session.commit()
    return db_user