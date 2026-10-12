"""서비스 계층에서 던지고, main.py 의 예외 핸들러가 HTTP 응답으로 변환한다."""


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ExternalServiceError(AppError):
    status_code = 502
    code = "external_service_error"
