from datetime import timedelta
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from app.core.redis import save_password_to_redis

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import get_request_logger
from app.core.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    revoke_refresh_token,
    verify_refresh_token,
    verify_password,
    )
from app.crud.auth_user import auth_user_crud
from app.crud.exceptions import (
    UserNotFoundError,
    DuplicateEmailError,
    DuplicateUsernameError
    )
from app.db.session import get_async_session
from app.messaging.rabbitmq import (
    publish_user_created,
    publish_user_updated,
    publish_user_deleted,
    publish_password_changed,
    publish_user_status_changed
)
from app.schemas.auth_user import (
    AuthUserCreate,
    AuthUserUpdate,
    AuthUserResponse,
    LogoutRequest,
    Token,
    RefreshTokenRequest
    )


router = APIRouter()

@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
async def register_auth_user(
    request: Request,
    user_in: AuthUserCreate
    ) -> Any:
    logger = get_request_logger(request)
    logger.info(f"ユーザー登録リクエスト: {user_in.username}")

    # ユーザー名とメールアドレスの重複チェック（実際のユーザー作成はuser-serviceで行われる）
    try:
        # パスワードをRedisに一時保存
        password_key = await save_password_to_redis(user_in.username, user_in.password)
        logger.info(f"パスワードを一時保存しました: key={password_key}")
        
        # ユーザー作成イベントの発行（パスワードを含めず、代わりにキー情報を含める）
        user_data = {
            "username": user_in.username,
            "email": user_in.email,
            "password_key": password_key
        }
        await publish_user_created(user_data)
        logger.info(f"ユーザー作成イベント発行: username={user_in.username}")
        
        # 202 Acceptedを返す（非同期処理が開始されたことを示す）
        return {
            "message": "ユーザー登録リクエストを受け付けました",
            "username": user_in.username,
            "email": user_in.email
        }
        
    except Exception as e:
        logger.error(f"ユーザー作成イベント発行失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="ユーザー登録リクエストの処理中にエラーが発生しました")

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    async_session: AsyncSession = Depends(get_async_session)
    ) -> Any:
    logger = get_request_logger(request)
    logger.info(f"ログインリクエスト: ユーザー名={form_data.username}")

    # ユーザー認証
    try:
        db_user = await auth_user_crud.get_by_username(async_session, username=form_data.username)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"ユーザー認証失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    # パスワード検証
    if not verify_password(form_data.password, db_user.hashed_password):
        logger.warning(f"ログイン失敗: ユーザー '{form_data.username}' のパスワードが不正です")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # アクセストークン生成
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(
        data={"sub": str(db_user.id),
              "user_id": str(db_user.user_id),
              "username": db_user.username},
        expires_delta=access_token_expires
    )
    
    # リフレッシュトークン生成
    refresh_token = await create_refresh_token(auth_user_id=str(db_user.id))

    logger.info(f"ログイン成功: ユーザーID={db_user.id}, ユーザー名={db_user.username}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(
    request: Request,
    token_data: LogoutRequest,
    async_session: AsyncSession = Depends(get_async_session)
    ) -> Any:
    """
    ログアウトしてリフレッシュトークンとアクセストークンを無効化するエンドポイント
    - アクセストークンとリフレッシュトークンの両方が必要
    - 両方のトークンを無効化する
    - 両方のトークンが正常に無効化された場合のみ成功とする
    """
    logger = get_request_logger(request)
    logger.info("ログアウトリクエスト")

    # トランザクション開始
    async with async_session.begin():
        try:
            # リフレッシュトークンを無効化
            refresh_result = await revoke_refresh_token(token_data.refresh_token)
            if not refresh_result:
                logger.warning(f"リフレッシュトークン無効化失敗: {token_data.refresh_token}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="リフレッシュトークンの無効化に失敗しました。ログアウトできません。"
                )
            
            # アクセストークンをブラックリストに登録
            blacklist_result = await blacklist_token(token_data.access_token)
            logger.info(f"アクセストークンのブラックリスト登録: {blacklist_result}")
            if not blacklist_result:
                logger.warning(f"アクセストークンブラックリスト登録失敗: {token_data.access_token}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="アクセストークンのブラックリスト登録に失敗しました。ログアウトできません。"
                )
            
            # 両方のトークンが正常に無効化された場合のみ成功
            logger.info("ログアウト処理完了: 両方のトークンが正常に無効化されました")
            return {"detail": "ログアウトしました"}
            
        except HTTPException:
            # 既に適切なHTTPExceptionが発生している場合はそのまま再スロー
            raise
        except JWTError as e:
            # JWT形式エラーは400 Bad Requestとして処理
            logger.error(f"JWTエラー: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"トークンの形式が不正です: {str(e)}"
            )
        except Exception as e:
            # その他の予期しないエラーは500 Internal Server Errorとして処理
            logger.error(f"ログアウト処理中にエラーが発生しました: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"ログアウト処理中にエラーが発生しました: {str(e)}"
            )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    token_data: RefreshTokenRequest,
    async_session: AsyncSession = Depends(get_async_session)
    ) -> Any:
    """
    リフレッシュトークンを使用して新しいアクセストークンを発行するエンドポイント
    - アクセストークンとリフレッシュトークンの両方が必要
    - 古いトークンは無効化される
    """
    logger = get_request_logger(request)
    logger.info("トークン更新リクエスト")

    # トランザクション開始
    async with async_session.begin():
        try:
            # リフレッシュトークンの検証
            try:
                auth_user_id = await verify_refresh_token(token_data.refresh_token)
            except jwt.JWTError as e:
                logger.warning(f"リフレッシュトークン検証失敗: JWT形式エラー: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="無効なリフレッシュトークンです",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except Exception as e:
                logger.warning(f"リフレッシュトークン検証失敗: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="リフレッシュトークンの検証に失敗しました",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # ユーザーの情報を取得
            try:
                db_user = await auth_user_crud.get_by_id(async_session, auth_user_id)
            except UserNotFoundError:
                logger.warning(f"ユーザー情報取得失敗: ユーザーが見つかりません: {auth_user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="ユーザーが見つかりません",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except Exception as e:
                logger.error(f"ユーザー情報取得失敗: {str(e)}")
                raise HTTPException(status_code=500, detail="Internal Server Error")
            
            # 古いリフレッシュトークンを無効化
            refresh_result = await revoke_refresh_token(token_data.refresh_token)
            if not refresh_result:
                logger.warning(f"リフレッシュトークン無効化に失敗: {token_data.refresh_token}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="リフレッシュトークンの無効化に失敗しました",
                )
            
            # 古いアクセストークンをブラックリストに登録
            blacklist_result = await blacklist_token(token_data.access_token)
            logger.info(f"アクセストークンブラックリスト登録: {blacklist_result}")
            if not blacklist_result:
                logger.warning(f"アクセストークンブラックリスト登録失敗: {token_data.access_token}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="古いアクセストークンのブラックリスト登録に失敗しました。トークンを更新できません。"
                )
            
            # 新しいアクセストークンを生成
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = await create_access_token(
            data={"sub": str(db_user.id),
                "user_id": str(db_user.user_id),
                "username": db_user.username},
            expires_delta=access_token_expires
            )

            # 新しいリフレッシュトークンを生成
            new_refresh_token = await create_refresh_token(auth_user_id=str(db_user.id))
            if not new_refresh_token:
                logger.warning("新しいリフレッシュトークンの生成に失敗")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="リフレッシュトークンの生成に失敗しました",
                )
            logger.info(f"トークン更新成功: ユーザーID={db_user.id}, ユーザー名={db_user.username}")
            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }
        except HTTPException:
            # HTTPExceptionはそのまま再スロー
            raise
        except JWTError as e:
            # JWTErrorは400 Bad Requestとして処理
            logger.error(f"JWTエラー: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"トークンの形式が不正です: {str(e)}"
            )
        except Exception as e:
            # その他の例外は500 Internal Server Errorとして処理
            logger.error(f"トークン更新中にエラー: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"トークンの更新中にエラーが発生しました: {str(e)}"
            )

@router.get("/me", response_model=AuthUserResponse)
async def get_user_me(current_user: AuthUserResponse = Depends(get_current_user)) -> Any:
    """
    現在のユーザー情報を取得するエンドポイント
    - 認証が必要
    """
    return current_user

@router.put("/users/{auth_user_id}")
async def update_user(auth_user_id: uuid.UUID,
                      user_update: AuthUserUpdate,
                      async_session: AsyncSession = Depends(get_async_session)):
    try:
        updated_user = await auth_user_crud.update_by_id(async_session, auth_user_id, user_update)
        return updated_user
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except DuplicateUsernameError:
        raise HTTPException(status_code=400, detail="Username already exists")
    # その他の例外処理...
