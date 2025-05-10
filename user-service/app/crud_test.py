import asyncio

from sqlalchemy import inspect

from app.crud.user import user_crud
from app.schemas.user import UserCreate
from app.db.init import Database
from app.db.session import async_engine, AsyncSessionLocal


async def main():
    
    # データベース初期化処理
    db = Database()
    await db.init()

    user_in = UserCreate(
        username="Koresawa Eisuke",
        email="eisuke_koresawa@example.com",
    )
    
    async with AsyncSessionLocal() as session:
        await user_crud.create(session, user_in)
        await session.commit()
        
if __name__ == "__main__":
    asyncio.run(main())