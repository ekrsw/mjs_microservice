from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

# このモジュール用のロガーを取得
logger = get_logger(__name__)


# 非同期エンジンの作成
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQLALCHEMY_ECHO,
    future=True
)

# 非同期セッションファクトリの作成
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# 非同期セッションジェネレータ
async def get_async_session() -> AsyncSession:
    logger.debug("Creating new database session")
    async with AsyncSessionLocal() as session:
        try:
            logger.debug("Database session created successfully")
            yield session
            logger.debug("Committing database session")
            await session.commit()
            logger.debug("Database session committed successfully")
        except Exception as e:
            # 例外発生時にロールバック
            logger.error(f"Exception occurred during database session, rolling back: {str(e)}")
            await session.rollback()
            raise # 例外を再スローして呼び出し元で処理できるようにする
