from collections import Counter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.core.logging import get_logger
from app.crud.exceptions import (
    UserNotFoundError,
    DuplicateUsernameError,
    DuplicateEmailError,
    DatabaseIntegrityError,
    DatabaseQueryError
    )
from app.models.user import User
from app.schemas.user import UserCreate

class CRUDUser:
    # クラスレベルのロガーの初期化
    logger = get_logger(__name__)
    async def create(self, session: AsyncSession, obj_in: UserCreate) -> User:
        self.logger.info(f"Creating new user: {obj_in.username}")
        try:
            db_obj = User(
                username=obj_in.username,
                email=obj_in.email,
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
    
    async def create_multiple(self, session: AsyncSession, obj_in_list: List[UserCreate]) -> List[User]:
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
        result = await session.execute(select(User).filter(User.username.in_(usernames)))
        existing_users_by_username = result.scalars().all()
        
        if existing_users_by_username:
            existing_username = existing_users_by_username[0].username
            self.logger.error(f"Failed to create multiple users: username '{existing_username}' already exists in database")
            raise DuplicateUsernameError(field="username", value=existing_username, 
                                        message=f"Username already exists: {existing_username}")
        
        # 4. データベースでの既存メールアドレスチェック（一括クエリ）
        result = await session.execute(select(User).filter(User.email.in_(emails)))
        existing_users_by_email = result.scalars().all()
        
        if existing_users_by_email:
            existing_email = existing_users_by_email[0].email
            self.logger.error(f"Failed to create multiple users: email '{existing_email}' already exists in database")
            raise DuplicateEmailError(field="email", value=existing_email, 
                                     message=f"Email already exists: {existing_email}")
        
        # 5. すべてのチェックが通過したら、ユーザーを作成
        db_objs = []
        for obj_in in obj_in_list:
            db_obj = User(
                username=obj_in.username,
                email=obj_in.email,
                is_suervisor=obj_in.is_supervisor,
                ctstage_name=obj_in.ctstage_name,
                sweet_name=obj_in.sweet_name,
                group_id=obj_in.group_id
            )
            db_objs.append(db_obj)
        session.add_all(db_objs)
        await session.flush()
        # commitはsessionのfinallyで行う
        self.logger.info(f"Successfully created {len(db_objs)} users")
        return db_objs
    
    async def get_all(self, session: AsyncSession) -> List[User]:
        self.logger.info("Retrieving all users")
        try:
            result = await session.execute(select(User))
            users = result.scalars().all()
            self.logger.info(f"Retrieved {len(users)} users")
            return users
        except Exception as e:
            self.logger.error(f"Error retrieving all users: {str(e)}")
            raise DatabaseQueryError(f"Failed to retrieve all users: {str(e)}") from e

    async def get_by_id(self, session: AsyncSession, id: uuid.UUID) -> User:
        self.logger.info(f"Retrieving user by id: {id}")
        result = await session.execute(select(User).filter(User.id == id))
        user = result.scalar_one_or_none()
        if user:
            self.logger.info(f"Found user with id: {id}")
        else:
            self.logger.warning(f"User with id {id} not found")
            raise UserNotFoundError(user_id=id)
        return user

user_crud = CRUDUser()
