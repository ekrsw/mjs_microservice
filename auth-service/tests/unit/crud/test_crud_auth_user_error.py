import pytest
import sqlite3
import uuid
from app.crud.auth_user import auth_user_crud
from app.crud.exceptions import (
    DuplicateEmailError,
    DuplicateUsernameError,
    DatabaseIntegrityError
    )
from app.schemas.auth_user import AuthUserCreate, AuthUserUpdate, AuthUserUpdatePassword


@pytest.mark.asyncio
async def test_create_auth_user_with_invalid_email(db_session, unique_username):
    """無効なメールアドレスでユーザーを作成しようとするとエラーが発生することを確認する"""
    invalid_email = "invalid_email"
    username = unique_username
    password = "password123"
    
    with pytest.raises(ValueError) as exc_info:
        await auth_user_crud.create(
            db_session,
            AuthUserCreate(
                username=username,
                email=invalid_email,
                password=password
            )
        )
    
    error = exc_info.value.errors()
    assert len(error) == 1
    assert error[0]["type"] == "value_error"
    assert error[0]["loc"] == ("email",)
    assert error[0]["msg"] == "value is not a valid email address: An email address must have an @-sign."

@pytest.mark.asyncio
async def test_create_auth_user_with_empty_username(db_session, unique_email, unique_password):
    """空のユーザー名でユーザーを作成しようとするとエラーが発生することを確認する"""
    username = ""
    email = unique_email
    password = unique_password
    
    with pytest.raises(ValueError) as exc_info:
        await auth_user_crud.create(
            db_session,
            AuthUserCreate(
                username=username,
                email=email,
                password=password
            )
        )
    
    error = exc_info.value.errors()
    assert len(error) == 1
    assert error[0]["type"] == "string_too_short"
    assert error[0]["loc"] == ("username",)
    assert error[0]["msg"] == "String should have at least 3 characters"

@pytest.mark.asyncio
async def test_create_auth_user_with_empty_password(db_session, unique_username, unique_email):
    """空のパスワードでユーザーを作成しようとするとエラーが発生することを確認する"""
    username = unique_username
    email = unique_email
    password = ""
    
    with pytest.raises(ValueError) as exc_info:
        await auth_user_crud.create(
            db_session,
            AuthUserCreate(
                username=username,
                email=email,
                password=password
            )
        )
    
    error = exc_info.value.errors()
    assert len(error) == 1
    assert error[0]["type"] == "string_too_short"
    assert error[0]["loc"] == ("password",)
    assert error[0]["msg"] == "String should have at least 1 character"

@pytest.mark.asyncio
async def test_create_auth_user_with_duplicate_username(db_session, test_user, unique_password):
    """重複したユーザー名でユーザーを作成しようとするとエラーが発生することを確認する"""
    username = test_user.username
    email = "test_user@example.com"
    password = unique_password
    user_in = AuthUserCreate(
        username=username,
        email=email,
        password=password
    )
    with pytest.raises(DuplicateUsernameError) as exc_info:
        await auth_user_crud.create(
            db_session,
            user_in
        )
    assert "Duplicate User" in str(exc_info.value)

@pytest.mark.asyncio
async def test_create_auth_user_with_duplicate_email(db_session, test_user, unique_password):
    """重複したメールアドレスでユーザーを作成しようとするとエラーが発生することを確認する"""
    username = "test_user2"
    email = test_user.email
    password = unique_password
    user_in = AuthUserCreate(
        username=username,
        email=email,
        password=password
    )
    with pytest.raises(DuplicateEmailError) as exc_info:
        await auth_user_crud.create(
            db_session,
            user_in
        )
    assert "Duplicate Email" in str(exc_info.value)

@pytest.mark.asyncio
async def test_create_auth_user_with_too_long_username(db_session, unique_email, unique_password):
    """ユーザー名が最大長（50文字）を超えた場合にエラーが発生することを確認する"""
    # 51文字のユーザー名を作成
    username = "a" * 51
    email = unique_email
    password = unique_password
    
    with pytest.raises(ValueError) as exc_info:
        await auth_user_crud.create(
            db_session,
            AuthUserCreate(
                username=username,
                email=email,
                password=password
            )
        )
    
    error = exc_info.value.errors()
    assert len(error) == 1
    assert error[0]["type"] == "string_too_long"
    assert error[0]["loc"] == ("username",)
    assert error[0]["msg"] == "String should have at most 50 characters"

@pytest.mark.asyncio
async def test_create_auth_user_with_too_long_password(db_session, unique_username, unique_email):
    """パスワードが最大長（16文字）を超えた場合にエラーが発生することを確認する"""
    username = unique_username
    email = unique_email
    # 17文字のパスワードを作成
    password = "a" * 17
    
    with pytest.raises(ValueError) as exc_info:
        await auth_user_crud.create(
            db_session,
            AuthUserCreate(
                username=username,
                email=email,
                password=password
            )
        )
    
    error = exc_info.value.errors()
    assert len(error) == 1
    assert error[0]["type"] == "string_too_long"
    assert error[0]["loc"] == ("password",)
    assert error[0]["msg"] == "String should have at most 16 characters"

@pytest.mark.asyncio
async def test_create_multiple_auth_users_with_duplicate_username_in_input(db_session):
    """入力データ内で重複するユーザー名がある場合にエラーが発生することを確認する"""
    # ユニークなシード値
    unique_id = str(uuid.uuid4())[:8]
    
    # 重複するユーザー名を持つユーザーデータを作成
    duplicate_username = f"duplicate_user_{unique_id}"
    
    users_data = [
        AuthUserCreate(
            username=duplicate_username,
            email=f"user1_{unique_id}@example.com",
            password="password1"
        ),
        AuthUserCreate(
            username=duplicate_username,  # 同じユーザー名を使用
            email=f"user2_{unique_id}@example.com",
            password="password2"
        )
    ]
    
    # エラーが発生することを確認
    with pytest.raises(DuplicateUsernameError) as exc_info:
        await auth_user_crud.create_multiple(db_session, users_data)
    
    # エラーメッセージを確認
    assert f"Duplicate username in input: {duplicate_username}" in str(exc_info.value)

@pytest.mark.asyncio
async def test_create_multiple_auth_users_with_duplicate_email_in_input(db_session):
    """入力データ内で重複するメールアドレスがある場合にエラーが発生することを確認する"""
    # ユニークなシード値
    unique_id = str(uuid.uuid4())[:8]
    
    # 重複するメールアドレスを持つユーザーデータを作成
    duplicate_email = f"duplicate_{unique_id}@example.com"
    
    users_data = [
        AuthUserCreate(
            username=f"user1_{unique_id}",
            email=duplicate_email,
            password="password1"
        ),
        AuthUserCreate(
            username=f"user2_{unique_id}",
            email=duplicate_email,  # 同じメールアドレスを使用
            password="password2"
        )
    ]
    
    # エラーが発生することを確認
    with pytest.raises(DuplicateEmailError) as exc_info:
        await auth_user_crud.create_multiple(db_session, users_data)
    
    # エラーメッセージを確認
    assert f"Duplicate email in input: {duplicate_email}" in str(exc_info.value)

@pytest.mark.asyncio
async def test_create_multiple_auth_users_with_existing_username(db_session, test_user):
    """データベースに既に存在するユーザー名がある場合にエラーが発生することを確認する"""
    # 既存のユーザー名を取得
    existing_username = test_user.username
    
    # ユニークなシード値
    unique_id = str(uuid.uuid4())[:8]
    
    # 既存のユーザー名を含むユーザーデータを作成
    users_data = [
        AuthUserCreate(
            username=f"new_user1_{unique_id}",
            email=f"new_user1_{unique_id}@example.com",
            password="password1"
        ),
        AuthUserCreate(
            username=existing_username,  # 既存のユーザー名を使用
            email=f"new_user2_{unique_id}@example.com",
            password="password2"
        )
    ]
    
    # エラーが発生することを確認
    with pytest.raises(DuplicateUsernameError) as exc_info:
        await auth_user_crud.create_multiple(db_session, users_data)
    
    # エラーメッセージを確認
    assert f"Username already exists: {existing_username}" in str(exc_info.value)

@pytest.mark.asyncio
async def test_create_multiple_auth_users_with_existing_email(db_session, test_user):
    """データベースに既に存在するメールアドレスがある場合にエラーが発生することを確認する"""
    # 既存のメールアドレスを取得
    existing_email = test_user.email
    
    # ユニークなシード値
    unique_id = str(uuid.uuid4())[:8]
    
    # 既存のメールアドレスを含むユーザーデータを作成
    users_data = [
        AuthUserCreate(
            username=f"new_user1_{unique_id}",
            email=f"new_user1_{unique_id}@example.com",
            password="password1"
        ),
        AuthUserCreate(
            username=f"new_user2_{unique_id}",
            email=existing_email,  # 既存のメールアドレスを使用
            password="password2"
        )
    ]
    
    # エラーが発生することを確認
    with pytest.raises(DuplicateEmailError) as exc_info:
        await auth_user_crud.create_multiple(db_session, users_data)
    
    # エラーメッセージを確認
    assert f"Email already exists: {existing_email}" in str(exc_info.value)

@pytest.mark.asyncio
async def test_update_auth_user_with_duplicate_username(db_session, test_user):
    """既存ユーザーと重複するユーザー名に更新しようとするとエラーが発生することを確認する"""
    # 既存のユーザー名を取得
    existing_username = test_user.username
    
    # 別のテスト用ユーザーを作成（一意のメールアドレスを使用）
    username = f"update_test_{uuid.uuid4().hex[:8]}"
    email = f"update_test_{uuid.uuid4().hex[:8]}@example.com"  # 一意のメールアドレス
    password = "password123"
    
    user_in = AuthUserCreate(
        username=username,
        email=email,
        password=password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # 既存のユーザー名に更新しようとする
    update_data = AuthUserUpdate(username=existing_username)
    
    # エラーが発生することを確認
    try:
        with pytest.raises(DuplicateUsernameError) as exc_info:
            await auth_user_crud.update_by_id(db_session, created_user.id, update_data)
        
        # エラーメッセージを確認
        assert "Username already exists" in str(exc_info.value)
    finally:
        # セッションをロールバックして後片付け
        await db_session.rollback()
        # ロールバック後は削除処理は不要（ロールバックによって変更が取り消される）

@pytest.mark.asyncio
async def test_update_auth_user_with_duplicate_email(db_session, test_user):
    """既存ユーザーと重複するメールアドレスに更新しようとするとエラーが発生することを確認する"""
    # 既存のメールアドレスを取得
    existing_email = test_user.email
    
    # 別のテスト用ユーザーを作成（一意のユーザー名とメールアドレスを使用）
    username = f"update_test_{uuid.uuid4().hex[:8]}"
    email = f"update_test_{uuid.uuid4().hex[:8]}@example.com"  # 一意のメールアドレス
    password = "password123"
    
    user_in = AuthUserCreate(
        username=username,
        email=email,
        password=password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # 既存のメールアドレスに更新しようとする
    update_data = AuthUserUpdate(email=existing_email)
    
    # エラーが発生することを確認
    try:
        with pytest.raises(DuplicateEmailError) as exc_info:
            await auth_user_crud.update_by_id(db_session, created_user.id, update_data)
        
        # エラーメッセージを確認
        assert "Email already exists" in str(exc_info.value)
    finally:
        # セッションをロールバックして後片付け
        await db_session.rollback()
        # ロールバック後は削除処理は不要（ロールバックによって変更が取り消される）

@pytest.mark.asyncio
async def test_update_auth_user_with_invalid_email(db_session):
    """無効なメールアドレスに更新しようとするとエラーが発生することを確認する"""
    # テスト用ユーザーを作成
    username = f"update_test_{uuid.uuid4().hex[:8]}"
    email = f"update_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    user_in = AuthUserCreate(
        username=username,
        email=email,
        password=password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # 無効なメールアドレスに更新しようとする
    invalid_email = "invalid_email"
    
    # エラーが発生することを確認
    with pytest.raises(ValueError) as exc_info:
        # AuthUserUpdateのインスタンス化時にバリデーションエラーが発生する
        update_data = AuthUserUpdate(email=invalid_email)
    
    # エラーメッセージを確認
    error = exc_info.value.errors()
    assert len(error) == 1
    assert error[0]["type"] == "value_error"
    assert error[0]["loc"] == ("email",)
    assert error[0]["msg"] == "value is not a valid email address: An email address must have an @-sign."
    
    # 後片付け
    await auth_user_crud.delete_by_id(db_session, created_user.id)

@pytest.mark.asyncio
async def test_update_auth_user_with_too_long_username(db_session):
    """長すぎるユーザー名に更新しようとするとエラーが発生することを確認する"""
    # テスト用ユーザーを作成
    username = f"update_test_{uuid.uuid4().hex[:8]}"
    email = f"update_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    user_in = AuthUserCreate(
        username=username,
        email=email,
        password=password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # 51文字のユーザー名（最大長は50文字）
    too_long_username = "a" * 51
    
    # エラーが発生することを確認
    with pytest.raises(ValueError) as exc_info:
        # AuthUserUpdateのインスタンス化時にバリデーションエラーが発生する
        update_data = AuthUserUpdate(username=too_long_username)
    
    # エラーメッセージを確認
    error = exc_info.value.errors()
    assert len(error) == 1
    assert error[0]["type"] == "string_too_long"
    assert error[0]["loc"] == ("username",)
    assert error[0]["msg"] == "String should have at most 50 characters"
    
    # 後片付け
    await auth_user_crud.delete_by_id(db_session, created_user.id)

@pytest.mark.asyncio
async def test_update_auth_user_with_empty_username(db_session):
    """空のユーザー名に更新しようとするとエラーが発生することを確認する"""
    # テスト用ユーザーを作成
    username = f"update_test_{uuid.uuid4().hex[:8]}"
    email = f"update_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    user_in = AuthUserCreate(
        username=username,
        email=email,
        password=password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # 空のユーザー名
    empty_username = ""
    
    # エラーが発生することを確認
    with pytest.raises(ValueError) as exc_info:
        # AuthUserUpdateのインスタンス化時にバリデーションエラーが発生する
        update_data = AuthUserUpdate(username=empty_username)
    
    # エラーメッセージを確認
    error = exc_info.value.errors()
    assert len(error) == 1
    assert error[0]["type"] == "string_too_short"
    assert error[0]["loc"] == ("username",)
    assert error[0]["msg"] == "String should have at least 3 characters"
    
    # 後片付け
    await auth_user_crud.delete_by_id(db_session, created_user.id)

@pytest.mark.asyncio
async def test_update_password_with_too_long_password(db_session):
    """長すぎるパスワードに更新しようとするとエラーが発生することを確認する"""
    # テスト用ユーザーを作成
    username = f"password_test_{uuid.uuid4().hex[:8]}"
    email = f"password_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    user_in = AuthUserCreate(
        username=username,
        email=email,
        password=password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # 17文字の長すぎるパスワード
    too_long_password = "a" * 17
    
    # エラーが発生することを確認
    with pytest.raises(ValueError) as exc_info:
        # AuthUserUpdatePasswordのインスタンス化時にバリデーションエラーが発生する
        update_data = AuthUserUpdatePassword(
            current_password=password,
            new_password=too_long_password
        )
    
    # エラーメッセージを確認
    error = exc_info.value.errors()
    assert len(error) == 1
    assert error[0]["type"] == "string_too_long"
    assert error[0]["loc"] == ("new_password",)
    assert error[0]["msg"] == "String should have at most 16 characters"
    
    # 後片付け
    await auth_user_crud.delete_by_id(db_session, created_user.id)

@pytest.mark.asyncio
async def test_update_password_with_empty_password(db_session):
    """空のパスワードに更新しようとした場合の挙動を確認する"""
    # テスト用ユーザーを作成
    username = f"password_test_{uuid.uuid4().hex[:8]}"
    email = f"password_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    user_in = AuthUserCreate(
        username=username,
        email=email,
        password=password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # 空のパスワード
    empty_password = ""
    
    # エラーが発生することを確認
    with pytest.raises(ValueError) as exc_info:
        # AuthUserUpdatePasswordのインスタンス化時にバリデーションエラーが発生する
        update_data = AuthUserUpdatePassword(
            current_password=password,
            new_password=empty_password
        )
    
    # エラーメッセージを確認
    error = exc_info.value.errors()
    assert len(error) == 1
    assert error[0]["type"] == "string_too_short"
    assert error[0]["loc"] == ("new_password",)
    assert error[0]["msg"] == "String should have at least 1 character"
    
    # 後片付け
    await auth_user_crud.delete_by_id(db_session, created_user.id)
