from app.config import get_settings
from app.errors import AppError, DatabaseConfigurationError
from app.schemas.responses import HealthResponse
from app.services.database import get_database_client


def build_health_response() -> HealthResponse:
    settings = get_settings()
    database_status = "not_configured"
    database_message = "Database environment variables are not configured."

    try:
        get_database_client().ping()
        database_status = "connected"
        database_message = "Database connection successful."
    except DatabaseConfigurationError as exc:
        database_message = exc.message
    except AppError as exc:
        database_status = "unavailable"
        database_message = exc.message

    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.app_env,
        version="0.1.0",
        database_status=database_status,
        database_message=database_message,
    )
