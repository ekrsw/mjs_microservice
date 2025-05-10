from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List

from app.core.logging import get_request_logger
from app.crud.user import user_crud
from app.db.session import get_async_session
from app.schemas.user import UserCreate
from app.crud.exceptions import (
    UserNotFoundError,
    DuplicateEmailError,
    DuplicateUsernameError
)

router = APIRouter()

@router.post("/users")
async def create_user(
    request: Request,
    user_in: UserCreate,
    async_session: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    ユーザーを作成するエンドポイント
    """
    logger = get_request_logger(request)
    logger.info(f"ユーザー作成リクエスト: {user_in.username}")
    
    try:
        new_user = await user_crud.create(async_session, user_in)
        # コミット前に必要な情報を変数に保存
        username = new_user.username
        user_id = new_user.id
        
        # トランザクションをコミット
        await async_session.commit()
        
        # 保存した変数を使用してログを出力
        logger.info(f"ユーザー作成成功: {username}, id: {user_id}")
        return {"status": "success", "message": "User created successfully", "user_id": str(user_id)}
    except DuplicateEmailError:
        logger.error(f"ユーザー作成失敗: メールアドレスが重複しています: {user_in.email}")
        raise HTTPException(status_code=400, detail="Email already exists")
    except DuplicateUsernameError:
        logger.error(f"ユーザー作成失敗: ユーザー名が重複しています: {user_in.username}")
        raise HTTPException(status_code=400, detail="Username already exists")
    except Exception as e:
        await async_session.rollback()
        logger.error(f"ユーザー作成失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/users")
async def get_users(
    request: Request,
    async_session: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    全ユーザーを取得するエンドポイント
    """
    logger = get_request_logger(request)
    logger.info("全ユーザー取得リクエスト")
    
    try:
        users = await user_crud.get_all(async_session)
        logger.info(f"全ユーザー取得成功: {len(users)}件")
        return users
    except Exception as e:
        logger.error(f"全ユーザー取得失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/users/{user_id}")
async def get_user(
    request: Request,
    user_id: str,
    async_session: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    指定したIDのユーザーを取得するエンドポイント
    """
    logger = get_request_logger(request)
    logger.info(f"ユーザー取得リクエスト: {user_id}")
    
    try:
        user = await user_crud.get_by_id(async_session, user_id)
        logger.info(f"ユーザー取得成功: {user.username}")
        return user
    except UserNotFoundError:
        logger.warning(f"ユーザー取得失敗: ユーザーが見つかりません: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"ユーザー取得失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
