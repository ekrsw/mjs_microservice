from collections import Counter
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.core.logging import get_logger
from app.core.security import get_password_hash, verify_password
from app.crud.exceptions import (
    UserNotFoundError,
    DuplicateUsernameError,
    DuplicateEmailError,
    DatabaseIntegrityError,
    DatabaseQueryError
    )
from app.models.auth_user import AuthUser
from app.schemas.auth_user import (
    AuthUserCreate,
    AuthUserUpdate,
    AuthUserUpdatePassword
    )

class CRUDAuthUser:
    # クラスレベルのロガーの初期化
    logger = get_logger(__name__)
    async def create(self, session: AsyncSession, obj_in: AuthUserCreate) -> AuthUser:
        self.logger.info(f"Creating new user with username: {obj_in.username}")
        try:
            db_obj = AuthUser(
                username=obj_in.username,
                email=obj_in.email,
                hashed_password=get_password_hash(obj_in.password)
            )
            session.add(db_obj)
            await session.flush()
            # commitはsessionのfinallyで行う
            self.logger.info(f"User created successfully: {db_obj.id}")
        except IntegrityError as e:
            # エラーメッセージやコードを検査して、具体的なエラータイプを特定
            if "username" in str(e.orig).lower():
                self.logger.error(f"Failed to create user: duplicate username '{obj_in.username}'")
                raise DuplicateUsernameError("Username already exists")
            elif "email" in str(e.orig).lower():
                self.logger.error(f"Failed to create user: duplicate email '{obj_in.email}'")
                raise DuplicateEmailError("Email already exists")
            else:
                # その他のIntegrityErrorの場合
                self.logger.error(f"Database integrity error while creating user: {str(e)}")
                raise DatabaseIntegrityError("Database integrity error") from e
        return db_obj
    
    async def create_with_user_id(self, session: AsyncSession, obj_in: AuthUserCreate, user_id: uuid.UUID) -> AuthUser:
        """
        user_idを指定してユーザーを作成する
        
        Args:
            session: データベースセッション
            obj_in: ユーザー作成スキーマ
            user_id: user-serviceから受け取ったユーザーID
            
        Returns:
            作成されたユーザー
        """
        self.logger.info(f"Creating new user with username: {obj_in.username} and user_id: {user_id}")
        try:
            db_obj = AuthUser(
                username=obj_in.username,
                email=obj_in.email,
                hashed_password=get_password_hash(obj_in.password),
                user_id=user_id
            )
            session.add(db_obj)
            await session.flush()
            # commitはsessionのfinallyで行う
            self.logger.info(f"User created successfully: {db_obj.id}, user_id: {db_obj.user_id}")
        except IntegrityError as e:
            # エラーメッセージやコードを検査して、具体的なエラータイプを特定
            if "username" in str(e.orig).lower():
                self.logger.error(f"Failed to create user: duplicate username '{obj_in.username}'")
                raise DuplicateUsernameError("Username already exists")
            elif "email" in str(e.orig).lower():
                self.logger.error(f"Failed to create user: duplicate email '{obj_in.email}'")
                raise DuplicateEmailError("Email already exists")
            elif "user_id" in str(e.orig).lower():
                self.logger.error(f"Failed to create user: duplicate user_id '{user_id}'")
                raise DatabaseIntegrityError("User ID already exists")
            else:
                # その他のIntegrityErrorの場合
                self.logger.error(f"Database integrity error while creating user: {str(e)}")
                raise DatabaseIntegrityError("Database integrity error") from e
        return db_obj
    
    async def create_multiple(self, session: AsyncSession, obj_in_list: List[AuthUserCreate]) -> List[AuthUser]:
        self.logger.info(f"Creating multiple users: {len(obj_in_list)} users")
        # 1. 入力データからusernameとemailのリストを抽出
        usernames = [obj_in.username for obj_in in obj_in_list]
        emails = [obj_in.email for obj_in in obj_in_list]
        
        # 2. 入力データ内での重複チェック
        duplicate_usernames = [username for username, count in Counter(usernames).items() if count > 1]
        duplicate_emails = [email for email, count in Counter(emails).items() if count > 1]
        
        if duplicate_usernames:
            self.logger.error(f"Failed to create multiple users: duplicate username '{duplicate_usernames[0]}' in input")
            raise DuplicateUsernameError(field="username", value=duplicate_usernames[0], 
                                        message=f"Duplicate username in input: {duplicate_usernames[0]}")
        
        if duplicate_emails:
            self.logger.error(f"Failed to create multiple users: duplicate email '{duplicate_emails[0]}' in input")
            raise DuplicateEmailError(field="email", value=duplicate_emails[0], 
                                     message=f"Duplicate email in input: {duplicate_emails[0]}")
        
        # 3. データベースでの既存ユーザー名チェック（一括クエリ）
        result = await session.execute(select(AuthUser).filter(AuthUser.username.in_(usernames)))
        existing_users_by_username = result.scalars().all()
        
        if existing_users_by_username:
            existing_username = existing_users_by_username[0].username
            self.logger.error(f"Failed to create multiple users: username '{existing_username}' already exists in database")
            raise DuplicateUsernameError(field="username", value=existing_username, 
                                        message=f"Username already exists: {existing_username}")
        
        # 4. データベースでの既存メールアドレスチェック（一括クエリ）
        result = await session.execute(select(AuthUser).filter(AuthUser.email.in_(emails)))
        existing_users_by_email = result.scalars().all()
        
        if existing_users_by_email:
            existing_email = existing_users_by_email[0].email
            self.logger.error(f"Failed to create multiple users: email '{existing_email}' already exists in database")
            raise DuplicateEmailError(field="email", value=existing_email, 
                                     message=f"Email already exists: {existing_email}")
        
        # 5. すべてのチェックが通過したら、ユーザーを作成
        db_objs = []
        for obj_in in obj_in_list:
            db_obj = AuthUser(
                username=obj_in.username,
                email=obj_in.email,
                hashed_password=get_password_hash(obj_in.password)
            )
            db_objs.append(db_obj)
        
        session.add_all(db_objs)
        await session.flush()
        # commitはsessionのfinallyで行う
        self.logger.info(f"Successfully created {len(db_objs)} users")
        return db_objs
    
    async def get_all(self, session: AsyncSession) -> List[AuthUser]:
        self.logger.info("Retrieving all users")
        try:
            result = await session.execute(select(AuthUser))
            users = result.scalars().all()
            self.logger.info(f"Retrieved {len(users)} users")
            return users
        except Exception as e:
            self.logger.error(f"Error retrieving all users: {str(e)}")
            raise DatabaseQueryError(f"Failed to retrieve all users: {str(e)}") from e
    
    async def get_by_id(self, session: AsyncSession, id: uuid.UUID) -> AuthUser:
        self.logger.info(f"Retrieving user by id: {id}")
        result = await session.execute(select(AuthUser).filter(AuthUser.id == id))
        user = result.scalar_one_or_none()
        if user:
            self.logger.info(f"Found user with id: {id}")
        else:
            self.logger.warning(f"User with id {id} not found")
            raise UserNotFoundError(user_id=id)
        return user
    
    async def get_by_username(self, session: AsyncSession, username: str) -> AuthUser:
        self.logger.info(f"Retrieving user by username: {username}")
        result = await session.execute(select(AuthUser).filter(AuthUser.username == username))
        user = result.scalar_one_or_none()
        if user:
            self.logger.info(f"Found user with username: {username}")
        else:
            self.logger.warning(f"User with username {username} not found")
            raise UserNotFoundError(username=username)
        return user
    
    async def get_by_email(self, session: AsyncSession, email: EmailStr) -> AuthUser:
        self.logger.info(f"Retrieving user by email: {email}")
        result = await session.execute(select(AuthUser).filter(AuthUser.email == email))
        user = result.scalar_one_or_none()
        if user:
            self.logger.info(f"Found user with email: {email}")
        else:
            self.logger.warning(f"User with email {email} not found")
            raise UserNotFoundError(message=f"User with email {email} not found")
        return user
    
    async def get_by_user_id(self, session: AsyncSession, user_id: uuid.UUID) -> AuthUser:
        self.logger.info(f"Retrieving user by user_id: {user_id}")
        result = await session.execute(select(AuthUser).filter(AuthUser.user_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            self.logger.info(f"Found user with user_id: {user_id}")
        else:
            self.logger.warning(f"User with user_id {user_id} not found")
            raise UserNotFoundError(user_id=user_id)
        return user
    
    async def update_by_id(self, session: AsyncSession, id: uuid.UUID, obj_in: AuthUserUpdate) -> AuthUser:
        self.logger.info(f"Updating user by id: {id}")
        db_obj = await self.get_by_id(session, id)
        update_fields = []
        if obj_in.username:
            self.logger.info(f"Updating username from '{db_obj.username}' to '{obj_in.username}'")
            db_obj.username = obj_in.username
            update_fields.append("username")
        if obj_in.email:
            self.logger.info(f"Updating email from '{db_obj.email}' to '{obj_in.email}'")
            db_obj.email = obj_in.email
            update_fields.append("email")
        # passowrdは別のメソッドで実装
        try:
            await session.flush()
            # commitはsessionのfinallyで行う
            self.logger.info(f"Successfully updated user {id}, fields: {', '.join(update_fields)}")
        except IntegrityError as e:
            # エラーメッセージやコードを検査して、具体的なエラータイプを特定
            if "username" in str(e.orig).lower():
                self.logger.error(f"Failed to update user: duplicate username '{obj_in.username}'")
                raise DuplicateUsernameError(message="Username already exists")
            elif "email" in str(e.orig).lower():
                self.logger.error(f"Failed to update user: duplicate email '{obj_in.email}'")
                raise DuplicateEmailError(message="Email already exists")
            else:
                # その他のIntegrityErrorの場合
                self.logger.error(f"Database integrity error while updating user: {str(e)}")
                raise DatabaseIntegrityError("Database integrity error") from e
        return db_obj
    
    async def update_by_username(self, session: AsyncSession, username: str, obj_in: AuthUserUpdate) -> AuthUser:
        self.logger.info(f"Updating user by username: {username}")
        db_obj = await self.get_by_username(session, username)
        update_fields = []
        if obj_in.username:
            self.logger.info(f"Updating username from '{db_obj.username}' to '{obj_in.username}'")
            db_obj.username = obj_in.username
            update_fields.append("username")
        if obj_in.email:
            self.logger.info(f"Updating email from '{db_obj.email}' to '{obj_in.email}'")
            db_obj.email = obj_in.email
            update_fields.append("email")
        # passowrdは別のメソッドで実装
        try:
            await session.flush()
            # commitはsessionのfinallyで行う
            self.logger.info(f"Successfully updated user with username {username}, fields: {', '.join(update_fields)}")
        except IntegrityError as e:
            # エラーメッセージやコードを検査して、具体的なエラータイプを特定
            if "username" in str(e.orig).lower():
                self.logger.error(f"Failed to update user: duplicate username '{obj_in.username}'")
                raise DuplicateUsernameError(message="Username already exists")
            elif "email" in str(e.orig).lower():
                self.logger.error(f"Failed to update user: duplicate email '{obj_in.email}'")
                raise DuplicateEmailError(message="Email already exists")
            else:
                # その他のIntegrityErrorの場合
                self.logger.error(f"Database integrity error while updating user: {str(e)}")
                raise DatabaseIntegrityError("Database integrity error") from e
        return db_obj

    async def update_password(self, session: AsyncSession, id: uuid.UUID, obj_in: AuthUserUpdatePassword) -> AuthUser:
        self.logger.info(f"Updating password for user with id: {id}")
        db_obj = await self.get_by_id(session, id)
        # 現在のパスワードが正しいか検証
        if not verify_password(obj_in.current_password, db_obj.hashed_password):
            self.logger.error(f"Failed to update password for user {id}: current password is incorrect")
            raise ValueError("Current password is incorrect")
            
        # 新しいパスワードに更新
        db_obj.hashed_password = get_password_hash(obj_in.new_password)
        await session.flush()
        # commitはsessionのfinallyで行う
        self.logger.info(f"Successfully updated password for user {id}")
        return db_obj
    
    async def delete_by_id(self, session: AsyncSession, id: uuid.UUID) -> AuthUser:
        self.logger.info(f"Deleting user by id: {id}")
        db_obj = await self.get_by_id(session, id)
        await session.delete(db_obj)
        await session.flush()
        # commitはsessionのfinallyで行う
        self.logger.info(f"Successfully deleted user with id: {id}")
        return db_obj
    
    async def delete_by_username(self, session: AsyncSession, username: str) -> AuthUser:
        self.logger.info(f"Deleting user by username: {username}")
        db_obj = await self.get_by_username(session, username)
        await session.delete(db_obj)
        await session.flush()
        # commitはsessionのfinallyで行う
        self.logger.info(f"Successfully deleted user with username: {username}")
        return db_obj

auth_user_crud = CRUDAuthUser()
