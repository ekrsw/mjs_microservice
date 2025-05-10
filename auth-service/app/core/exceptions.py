class AppException(Exception):
    """アプリケーションのベース例外クラス"""
    def __init__(self, message: str = "An application error occurred"):
        self.message = message
        super().__init__(self.message)

class ResourceNotFoundError(AppException):
    """リソースが見つからない場合の例外"""
    def __init__(self, resource_type: str, resource_id=None, message=None):
        self.resource_type = resource_type
        self.resource_id = resource_id
        default_message = f"{resource_type} not found"
        if resource_id:
            default_message += f" (id: {resource_id})"
        self.message = message or default_message
        super().__init__(self.message)

class ValidationError(AppException):
    """バリデーションエラー"""
    def __init__(self, field: str = None, details: str = None, message: str = None):
        self.field = field
        self.details = details
        default_message = "Validation error"
        if field:
            default_message += f" for field '{field}'"
        if details:
            default_message += f": {details}"
        self.message = message or default_message
        super().__init__(self.message)
        
class DuplicateResourceError(AppException):
    """リソースの重複エラー"""
    def __init__(self, resource_type: str, field: str = None, value = None, message: str = None):
        self.resource_type = resource_type
        self.field = field
        self.value = value
        default_message = f"Duplicate {resource_type}"
        if field and value:
            default_message += f" with {field}='{value}'"
        self.message = message or default_message
        super().__init__(self.message)