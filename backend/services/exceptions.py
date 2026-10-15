class AppError(Exception):
    """Base application exception with error code and HTTP status code."""
    def __init__(self, message, code="Error", status_code=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

    def to_dict(self):
        return {
            "error": self.code,
            "message": self.message
        }

class ValidationError(AppError):
    def __init__(self, message):
        super().__init__(message, code="ValidationError", status_code=400)

class NotFoundError(AppError):
    def __init__(self, message):
        super().__init__(message, code="NotFoundError", status_code=404)

class PersistenceError(AppError):
    def __init__(self, message):
        super().__init__(message, code="PersistenceError", status_code=500)

class AuthorizationError(AppError):
    def __init__(self, message="Access denied."):
        super().__init__(message, code="Forbidden", status_code=403)
