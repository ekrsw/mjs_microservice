import asyncio

from sqlalchemy import inspect

from app.crud.auth_user import auth_user_crud
from app.schemas.auth_user import AuthUserCreate, AuthUserUpdate, AuthUserUpdatePassword
from app.db.init import Database
from app.db.session import async_engine, AsyncSessionLocal


async def main():
    
    # データベース初期化処理
    db = Database()
    await db.init()

    # 登録するユーザー情報
    """users_in = [
        AuthUserCreate(username="Koresawa Eisuke",email="eisuke_koresawa@gmail.com",password="password123"),
        AuthUserCreate(username="Yamada Hanako",email="hanako_yamada@gmail.com",password="password123"),
        AuthUserCreate(username="Sakamoto Yoshiyuki",email="yoshiyuki_sakamoto@gmail.com",password="password123"),
        AuthUserCreate(username="Yoshida Taro",email="taro_yoshida@gmail.com",password="password123")
    ]"""

    # user_in = AuthUserCreate(username="Koresawa Eisuke",email="eisuke_koresawa@gmail.com",password="password123")
    # user_in = AuthUserUpdate(userna="eisuke_koresawa")
    user_in = AuthUserUpdatePassword(current_password="password123", new_password="new_password123")
    async with AsyncSessionLocal() as session:
        await auth_user_crud.update_password(session, "3da65b3f-a6b3-47e6-85e6-555e34af6dff", user_in)
        await session.commit()
        
if __name__ == "__main__":
    asyncio.run(main())