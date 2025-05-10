from app.db.base import Base
from app.db.session import async_engine


class Database:
    async def init(self):
        # 初期処理。テーブルを作成する。
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)