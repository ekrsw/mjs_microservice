from app.core.exceptions import ResourceNotFoundError, DuplicateResourceError

class UserNotFoundError(ResourceNotFoundError):
    """ユーザーが見つからない場合の例外"""
    def __init__(self, user_id=None, username=None, message=None):
        resource_id = user_id or username
        super().__init__("User", resource_id, message)
        self.user_id = user_id
        self.username = username

class DuplicateUsernameError(DuplicateResourceError):
    """ユーザーの重複エラー"""
    def __init__(self, field: str = None, value = None, message: str = None):
        super().__init__("User", field, value, message)

class DuplicateEmailError(DuplicateResourceError):
    """メールアドレスの重複エラー"""
    def __init__(self, field: str = None, value = None, message: str = None):
        super().__init__("Email", field, value, message)

class DatabaseIntegrityError(Exception):
    """データベースの整合性エラー"""
    def __init__(self, message: str = "Database integrity error"):
        self.message = message
        super().__init__(self.message)

class DatabaseQueryError(Exception):
    """データベースクエリ実行エラー"""
    def __init__(self, message: str = "Database query execution error"):
        self.message = message
        super().__init__(self.message)

class DuplicateGroupNameError(DuplicateResourceError):
    """グループ名の重複エラー"""
    def __init__(self, field: str = None, value = None, message: str = None):
        super().__init__("Group", field, value, message)