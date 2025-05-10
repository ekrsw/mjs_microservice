import pytest
import uuid

from app.core.security import verify_password
from app.crud.auth_user import auth_user_crud
from app.crud.exceptions import UserNotFoundError
from app.schemas.auth_user import AuthUserCreate, AuthUserUpdate, AuthUserUpdatePassword


@pytest.mark.asyncio
async def test_create_auth_user(db_session, unique_username, unique_email, unique_password):
    """ユーザーの作成をテストする"""
    username = unique_username
    email = unique_email
    password = unique_password
    user_in = AuthUserCreate(
        username=username,
        email=email,
        password=password
        )
    db_user = await auth_user_crud.create(db_session, user_in)
    
    # ユーザーが正しく作成されたか確認する
    assert db_user.username == username
    assert db_user.email == email
    assert db_user.hashed_password != password
    assert verify_password(password, db_user.hashed_password) is True
    assert verify_password("wrong_password", db_user.hashed_password) is False

    # ユーザーがデータベースに正しく保存されているか確認する
    new_user = await auth_user_crud.get_by_username(db_session, username)
    assert new_user is not None
    assert new_user.username == username
    assert new_user.email == email
    assert verify_password(password, new_user.hashed_password) is True
    assert verify_password("wrong_password", new_user.hashed_password) is False

    # ユーザーがデータベースに正しく保存されているかをIDで確認する
    new_user_by_id = await auth_user_crud.get_by_id(db_session, db_user.id)
    assert new_user_by_id is not None
    assert new_user_by_id.id == db_user.id
    assert new_user_by_id.username == username
    assert new_user_by_id.email == email
    assert verify_password(password, new_user_by_id.hashed_password) is True
    assert verify_password("wrong_password", new_user_by_id.hashed_password) is False

    # 後片付け
    await auth_user_crud.delete_by_id(db_session, db_user.id)
    try:
        result = await auth_user_crud.get_by_username(db_session, username)
        assert False, "Expected UserNotFoundError but no exception was raised"
    except UserNotFoundError:
        pass
    except Exception as e:
        assert False, f"Expected UserNotFoundError but got {type(e).__name__}: {str(e)}"

@pytest.mark.asyncio
async def test_create_multiple_auth_users(db_session):
    """複数ユーザーを一括作成できることをテストする"""
    # 3人のユーザーデータを作成
    users_data = []
    user_count = 3
    expected_usernames = []
    expected_emails = []
    expected_passwords = []
    
    for i in range(user_count):
        # ユニークなシード値
        unique_id = str(uuid.uuid4())[:8]  # UUIDの最初の8文字だけ使用
        
        username = f"test_user_{i}_{unique_id}"
        email = f"test_user_{i}_{unique_id}@example.com"
        # 16文字以内のパスワードを生成
        password = f"pass_{i}_{unique_id}"
        
        expected_usernames.append(username)
        expected_emails.append(email)
        expected_passwords.append(password)
        
        users_data.append(
            AuthUserCreate(
                username=username,
                email=email,
                password=password
            )
        )
    
    # 複数ユーザーを一括作成
    created_users = await auth_user_crud.create_multiple(db_session, users_data)
    
    # 作成されたユーザー数を確認
    assert len(created_users) == user_count
    
    # 各ユーザーが正しく作成されているか確認
    for i, user in enumerate(created_users):
        # ユーザー情報が正しいことを確認
        assert user.username == expected_usernames[i]
        assert user.email == expected_emails[i]
        assert user.hashed_password != expected_passwords[i]  # パスワードはハッシュ化されているはず
        assert verify_password(expected_passwords[i], user.hashed_password) is True
        
        # ユーザーがDBに正しく保存されているか確認
        db_user = await auth_user_crud.get_by_username(db_session, expected_usernames[i])
        assert db_user is not None
        assert db_user.username == expected_usernames[i]
        assert db_user.email == expected_emails[i]
        assert verify_password(expected_passwords[i], db_user.hashed_password) is True
    
    # すべてのユーザーをDBから取得できることを確認
    all_users = await auth_user_crud.get_all(db_session)
    assert len(all_users) >= user_count  # 他のテストで作成されたユーザーも含まれる可能性がある
    
    # 後片付け（作成したユーザーを削除）
    for user in created_users:
        await auth_user_crud.delete_by_id(db_session, user.id)
    
    # 削除されたことを確認
    for username in expected_usernames:
        try:
            result = await auth_user_crud.get_by_username(db_session, username)
            assert False, "Expected UserNotFoundError but no exception was raised"
        except UserNotFoundError:
            pass
        except Exception as e:
            assert False, f"Expected UserNotFoundError but got {type(e).__name__}: {str(e)}"

@pytest.mark.asyncio
async def test_get_auth_user_by_email(db_session, unique_username, unique_email, unique_password):
    """メールアドレスからユーザーを取得できることをテストする"""
    # テスト用のユーザーを作成
    username = unique_username
    email = unique_email
    password = unique_password
    
    # ユーザーを作成
    user_in = AuthUserCreate(
        username=username,
        email=email,
        password=password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # メールアドレスでユーザーを取得
    retrieved_user = await auth_user_crud.get_by_email(db_session, email)
    
    # 取得したユーザーが正しいことを確認
    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id
    assert retrieved_user.username == username
    assert retrieved_user.email == email
    assert verify_password(password, retrieved_user.hashed_password) is True
    
    # 存在しないメールアドレスの場合はUserNotFoundErrorが返ることを確認
    non_existent_email = f"non_existent_{uuid.uuid4()}@example.com"
    try:
        non_existent_user = await auth_user_crud.get_by_email(db_session, non_existent_email)
        assert False, "Expected UserNotFoundError but no exception was raised"
    except UserNotFoundError:
        pass
    except Exception as e:
        assert False, f"Expected UserNotFoundError but got {type(e).__name__}: {str(e)}"
    
    # 後片付け
    await auth_user_crud.delete_by_id(db_session, created_user.id)
    try:
        result = await auth_user_crud.get_by_email(db_session, email)
        assert False, "Expected UserNotFoundError but no exception was raised"
    except UserNotFoundError:
        pass
    except Exception as e:
        assert False, f"Expected UserNotFoundError but got {type(e).__name__}: {str(e)}"

@pytest.mark.asyncio
async def test_get_all_auth_users(db_session):
    """全ユーザーを取得できることをテストする"""
    # テスト前に既存のユーザー数を取得
    initial_users = await auth_user_crud.get_all(db_session)
    initial_count = len(initial_users)
    
    # テスト用に複数のユーザーを作成
    user_count = 3
    created_users = []
    
    for i in range(user_count):
        # ユニークな識別子
        unique_id = str(uuid.uuid4())[:8]
        
        username = f"get_all_test_user_{i}_{unique_id}"
        email = f"get_all_test_{i}_{unique_id}@example.com"
        password = f"pass_{i}_{unique_id}"  # 16文字以内
        
        user_in = AuthUserCreate(
            username=username,
            email=email,
            password=password
        )
        
        # ユーザーを作成
        db_user = await auth_user_crud.create(db_session, user_in)
        created_users.append(db_user)
    
    # 全ユーザーを取得
    all_users = await auth_user_crud.get_all(db_session)
    
    # ユーザー数が期待通りに増えていることを確認
    assert len(all_users) == initial_count + user_count
    
    # 作成したユーザーがすべて取得結果に含まれていることを確認
    created_user_ids = [user.id for user in created_users]
    retrieved_user_ids = [user.id for user in all_users]
    
    for user_id in created_user_ids:
        assert user_id in retrieved_user_ids
    
    # 後片付け：作成したすべてのユーザーを削除
    for user in created_users:
        await auth_user_crud.delete_by_id(db_session, user.id)
    
    # 削除後のユーザー数が元の数に戻っていることを確認
    final_users = await auth_user_crud.get_all(db_session)
    assert len(final_users) == initial_count

@pytest.mark.asyncio
async def test_get_auth_user_by_nonexistent_id(db_session):
    """存在しないIDでユーザーを取得しようとした場合、UserNotFoundErrorが返ることを確認する"""
    # 存在しないUUID（ランダムに生成）
    nonexistent_id = uuid.uuid4()
    
    # 存在しないIDでユーザーを取得
    try:
        user = await auth_user_crud.get_by_id(db_session, nonexistent_id)
        assert False, "Expected UserNotFoundError but no exception was raised"
    except UserNotFoundError:
        pass
    except Exception as e:
        assert False, f"Expected UserNotFoundError but got {type(e).__name__}: {str(e)}"
    
    # DBに実際にユーザーが存在しないことを再確認（全ユーザー取得）
    all_users = await auth_user_crud.get_all(db_session)
    all_user_ids = [user.id for user in all_users]
    assert nonexistent_id not in all_user_ids

@pytest.mark.asyncio
async def test_get_auth_user_by_nonexistent_username(db_session):
    """存在しないユーザー名でユーザーを取得しようとした場合、UserNotFoundErrorが返ることを確認する"""
    # 存在しないユーザー名を生成（ランダムなUUIDを使用して一意性を確保）
    nonexistent_username = f"nonexistent_user_{uuid.uuid4()}"
    
    # 事前確認：このユーザー名が実際にDBに存在しないことを確認
    all_users = await auth_user_crud.get_all(db_session)
    for user in all_users:
        assert user.username != nonexistent_username
    
    # 存在しないユーザー名でユーザーを取得
    try:
        user = await auth_user_crud.get_by_username(db_session, nonexistent_username)
        assert False, "Expected UserNotFoundError but no exception was raised"
    except UserNotFoundError:
        pass
    except Exception as e:
        assert False, f"Expected UserNotFoundError but got {type(e).__name__}: {str(e)}"

@pytest.mark.asyncio
async def test_get_auth_user_by_nonexistent_email(db_session):
    """存在しないメールアドレスでユーザーを取得しようとした場合、UserNotFoundErrorが返ることを確認する"""
    # 存在しないメールアドレスを生成（ランダムなUUIDを使用して一意性を確保）
    nonexistent_email = f"nonexistent_{uuid.uuid4()}@example.com"
    
    # 事前確認：このメールアドレスが実際にDBに存在しないことを確認
    all_users = await auth_user_crud.get_all(db_session)
    for user in all_users:
        assert user.email != nonexistent_email
    
    # 存在しないメールアドレスでユーザーを取得
    # EmailStrをインスタンス化せずに、直接文字列を渡す
    try:
        user = await auth_user_crud.get_by_email(db_session, nonexistent_email)
        assert False, "Expected UserNotFoundError but no exception was raised"
    except UserNotFoundError:
        pass
    except Exception as e:
        assert False, f"Expected UserNotFoundError but got {type(e).__name__}: {str(e)}"

@pytest.mark.asyncio
async def test_update_auth_user_username(db_session, unique_username, unique_email, unique_password):
    """ユーザー名を更新できることを確認する"""
    # テスト用のユーザーを作成
    original_username = unique_username
    email = unique_email
    password = unique_password
    
    user_in = AuthUserCreate(
        username=original_username,
        email=email,
        password=password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # 新しいユーザー名を生成
    new_username = f"updated_{uuid.uuid4().hex[:10]}"
    
    # ユーザー名を更新
    update_data = AuthUserUpdate(username=new_username)
    updated_user = await auth_user_crud.update_by_id(db_session, created_user.id, update_data)
    
    # 更新されたことを確認
    assert updated_user.username == new_username
    assert updated_user.email == email  # メールアドレスは変更されていないことを確認
    
    # DBに正しく反映されているか確認
    db_user = await auth_user_crud.get_by_id(db_session, created_user.id)
    assert db_user is not None
    assert db_user.username == new_username
    assert db_user.email == email
    
    # 元のユーザー名で検索するとユーザーが見つからないことを確認
    try:
        old_user = await auth_user_crud.get_by_username(db_session, original_username)
        assert False, "Expected UserNotFoundError but no exception was raised"
    except UserNotFoundError:
        pass
    except Exception as e:
        assert False, f"Expected UserNotFoundError but got {type(e).__name__}: {str(e)}"

    # 後片付け
    await auth_user_crud.delete_by_id(db_session, created_user.id)

@pytest.mark.asyncio
async def test_update_auth_user_email(db_session, unique_username, unique_email, unique_password):
    """メールアドレスを更新できることを確認する"""
    # テスト用のユーザーを作成
    username = unique_username
    original_email = unique_email
    password = unique_password
    
    user_in = AuthUserCreate(
        username=username,
        email=original_email,
        password=password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # 新しいメールアドレスを生成
    new_email = f"updated_{uuid.uuid4().hex[:10]}@example.com"
    
    # メールアドレスを更新
    update_data = AuthUserUpdate(email=new_email)
    updated_user = await auth_user_crud.update_by_id(db_session, created_user.id, update_data)
    
    # 更新されたことを確認
    assert updated_user.email == new_email
    assert updated_user.username == username  # ユーザー名は変更されていないことを確認
    
    # DBに正しく反映されているか確認
    db_user = await auth_user_crud.get_by_id(db_session, created_user.id)
    assert db_user is not None
    assert db_user.email == new_email
    assert db_user.username == username
    
    # 元のメールアドレスで検索するとユーザーが見つからないことを確認
    try:
        old_user = await auth_user_crud.get_by_email(db_session, original_email)
        assert False, "Expected UserNotFoundError but no exception was raised"
    except UserNotFoundError:
        pass
    except Exception as e:
        assert False, f"Expected UserNotFoundError but got {type(e).__name__}: {str(e)}"
    
    # 後片付け
    await auth_user_crud.delete_by_id(db_session, created_user.id)

@pytest.mark.asyncio
async def test_update_auth_user_password(db_session, unique_username, unique_email):
    """パスワードを更新できることを確認する"""
    # テスト用のユーザーを作成
    username = unique_username
    email = unique_email
    original_password = "password123"
    
    user_in = AuthUserCreate(
        username=username,
        email=email,
        password=original_password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # 新しいパスワードを生成
    new_password = "newpassword456"
    
    # パスワードを更新
    update_data = AuthUserUpdatePassword(
        current_password=original_password,
        new_password=new_password
    )
    updated_user = await auth_user_crud.update_password(db_session, created_user.id, update_data)
    
    # 基本情報は変更されていないことを確認
    assert updated_user.username == username
    assert updated_user.email == email
    
    # パスワードが正しく更新されていることを確認
    assert verify_password(new_password, updated_user.hashed_password) is True
    assert verify_password(original_password, updated_user.hashed_password) is False
    
    # 誤ったパスワードではエラーが発生することを確認
    with pytest.raises(ValueError, match="Current password is incorrect"):
        wrong_update = AuthUserUpdatePassword(
            current_password="wrong_password",
            new_password="another_password"
        )
        await auth_user_crud.update_password(db_session, created_user.id, wrong_update)
    
    # 後片付け
    await auth_user_crud.delete_by_id(db_session, created_user.id)


@pytest.mark.asyncio
async def test_update_auth_user_by_username(db_session, unique_username, unique_email, unique_password):
    """ユーザー名からユーザー情報を更新できることを確認する"""
    # テスト用のユーザーを作成
    original_username = unique_username
    original_email = unique_email
    password = unique_password
    
    user_in = AuthUserCreate(
        username=original_username,
        email=original_email,
        password=password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # 新しい情報を生成
    new_email = f"updated_by_username_{uuid.uuid4().hex[:10]}@example.com"
    
    # ユーザー名からユーザー情報を更新
    update_data = AuthUserUpdate(email=new_email)
    updated_user = await auth_user_crud.update_by_username(db_session, original_username, update_data)
    
    # 更新されたことを確認
    assert updated_user.email == new_email
    assert updated_user.username == original_username  # ユーザー名は変更されていないことを確認
    
    # DBに正しく反映されているか確認
    db_user = await auth_user_crud.get_by_id(db_session, created_user.id)
    assert db_user is not None
    assert db_user.email == new_email
    assert db_user.username == original_username
    
    # 後片付け
    await auth_user_crud.delete_by_id(db_session, created_user.id)

@pytest.mark.asyncio
async def test_update_auth_user_username_by_username(db_session, unique_username, unique_email, unique_password):
    """ユーザー名を使ってユーザー名自体を更新できることを確認する"""
    # テスト用のユーザーを作成
    original_username = unique_username
    email = unique_email
    password = unique_password
    
    user_in = AuthUserCreate(
        username=original_username,
        email=email,
        password=password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # 新しいユーザー名を生成
    new_username = f"updated_username_{uuid.uuid4().hex[:10]}"
    
    # ユーザー名からユーザー名を更新
    update_data = AuthUserUpdate(username=new_username)
    updated_user = await auth_user_crud.update_by_username(db_session, original_username, update_data)
    
    # 更新されたことを確認
    assert updated_user.username == new_username
    assert updated_user.email == email  # メールアドレスは変更されていないことを確認
    
    # DBに正しく反映されているか確認
    db_user = await auth_user_crud.get_by_id(db_session, created_user.id)
    assert db_user is not None
    assert db_user.username == new_username
    assert db_user.email == email
    
    # 元のユーザー名で検索するとユーザーが見つからないことを確認
    try:
        old_user = await auth_user_crud.get_by_username(db_session, original_username)
        assert False, "Expected UserNotFoundError but no exception was raised"
    except UserNotFoundError:
        pass
    
    # 後片付け
    await auth_user_crud.delete_by_id(db_session, created_user.id)

@pytest.mark.asyncio
async def test_delete_auth_user_by_username(db_session, unique_username, unique_email, unique_password):
    """ユーザー名からユーザーを削除できることを確認する"""
    # テスト用のユーザーを作成
    username = unique_username
    email = unique_email
    password = unique_password
    
    user_in = AuthUserCreate(
        username=username,
        email=email,
        password=password
    )
    created_user = await auth_user_crud.create(db_session, user_in)
    
    # ユーザーが作成されたことを確認
    db_user = await auth_user_crud.get_by_username(db_session, username)
    assert db_user is not None
    assert db_user.id == created_user.id
    
    # ユーザー名を使ってユーザーを削除
    deleted_user = await auth_user_crud.delete_by_username(db_session, username)
    
    # 削除されたユーザーの情報を確認
    assert deleted_user.id == created_user.id
    assert deleted_user.username == username
    assert deleted_user.email == email
    
    # 実際にDBから削除されたことを確認（ユーザー名で検索）
    try:
        result = await auth_user_crud.get_by_username(db_session, username)
        assert False, "Expected UserNotFoundError but no exception was raised"
    except UserNotFoundError:
        pass
    
    # IDでも検索できないことを確認
    try:
        result = await auth_user_crud.get_by_id(db_session, created_user.id)
        assert False, "Expected UserNotFoundError but no exception was raised"
    except UserNotFoundError:
        pass
