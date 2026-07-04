import logging
from dataclasses import dataclass, field

from fastapi.exceptions import RequestValidationError
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass
class AppError(Exception):
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"
    details: dict[str, str] = field(default_factory=dict)


class DomainError(AppError):
    pass


class InfrastructureError(AppError):
    pass


class ConfigurationError(InfrastructureError):
    def __init__(self, message: str = "Application configuration is invalid.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="configuration_error",
        )


class DatabaseConfigurationError(InfrastructureError):
    def __init__(self, message: str = "Database configuration is incomplete.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="database_configuration_error",
        )


class DatabaseConnectionError(InfrastructureError):
    def __init__(self, message: str = "Database connection failed.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="database_connection_error",
        )


class DatabaseQueryError(InfrastructureError):
    def __init__(self, message: str = "Database query failed.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="database_query_error",
        )


class AnalyticsValidationError(DomainError):
    def __init__(self, message: str = "Analytics input is invalid.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="analytics_validation_error",
        )


class AmbiguousQueryError(DomainError):
    def __init__(self, message: str = "The query is ambiguous and needs reformulation.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="ambiguous_query_error",
        )


class LLMConfigurationError(InfrastructureError):
    def __init__(self, message: str = "LLM configuration is incomplete.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="llm_configuration_error",
        )


class LLMInvocationError(InfrastructureError):
    def __init__(self, message: str = "LLM request failed.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="llm_invocation_error",
        )


class ObservabilityError(InfrastructureError):
    def __init__(self, message: str = "Observability instrumentation failed.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="observability_error",
        )


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    log_method = logger.error if exc.status_code >= 500 else logger.warning
    log_method("Handled application error [%s]: %s", exc.code, exc.message)
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


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details: dict[str, str] = {}
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", []) if part != "body")
        key = location or "request"
        details[key] = error.get("msg", "Invalid request.")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "The request payload is invalid.",
                "details": details,
            }
        },
    )


async def unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
    logger.exception("Unhandled application exception.")
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
