from dataclasses import dataclass, field

from fastapi import Request, status
from fastapi.responses import JSONResponse


@dataclass
class AppError(Exception):
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"
    details: dict[str, str] = field(default_factory=dict)


class ConfigurationError(AppError):
    def __init__(self, message: str = "Application configuration is invalid.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="configuration_error",
        )


class DatabaseConfigurationError(AppError):
    def __init__(self, message: str = "Database configuration is incomplete.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="database_configuration_error",
        )


class DatabaseConnectionError(AppError):
    def __init__(self, message: str = "Database connection failed.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="database_connection_error",
        )


class DatabaseQueryError(AppError):
    def __init__(self, message: str = "Database query failed.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="database_query_error",
        )


class AnalyticsValidationError(AppError):
    def __init__(self, message: str = "Analytics input is invalid.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="analytics_validation_error",
        )


class LLMConfigurationError(AppError):
    def __init__(self, message: str = "LLM configuration is incomplete.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="llm_configuration_error",
        )


class LLMInvocationError(AppError):
    def __init__(self, message: str = "LLM request failed.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="llm_invocation_error",
        )


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected error occurred.",
                "details": {},
            }
        },
    )
