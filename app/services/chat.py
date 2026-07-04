import logging
from uuid import uuid4

from app.agent.assistant import run_assistant
from app.core.errors import (
    AppError,
    ConfigurationError,
    DatabaseConnectionError,
    DatabaseQueryError,
    LLMConfigurationError,
)
from app.schemas.responses import ChatMeta, ChatResponse

logger = logging.getLogger(__name__)


def fallback_answer_for_error(exc: Exception) -> str:
    if isinstance(exc, (DatabaseConnectionError, DatabaseQueryError)):
        return (
            "No pude consultar la base de datos en este momento. "
            "Si queres, probemos de nuevo en unos minutos."
        )
    if isinstance(exc, (ConfigurationError, LLMConfigurationError)):
        return (
            "El asistente no esta completamente configurado para responder esta consulta en este momento."
        )
    if isinstance(exc, AppError):
        return exc.message
    return (
        "Tuvimos un problema inesperado procesando la consulta. "
        "Si queres, reformulala o intentemos nuevamente."
    )


def build_fallback_chat_response(message: str, thread_id: str | None, exc: Exception) -> ChatResponse:
    resolved_thread_id = thread_id or f"thread-{uuid4().hex[:12]}"
    answer = fallback_answer_for_error(exc)
    if isinstance(exc, AppError):
        logger.warning("Returning degraded chat response for message: %s due to %s", message, exc.code)
    else:
        logger.exception("Returning degraded chat response for message: %s", message)

    return ChatResponse(
        answer=answer,
        intent="unsupported",
        data_range=None,
        chart=None,
        meta=ChatMeta(
            thread_id=resolved_thread_id,
            warnings=[answer],
            last_data_date=None,
            source="service-fallback",
            model=None,
            trace_id=None,
            trace_url=None,
            prompts=[],
        ),
    )


def build_chat_response(message: str, thread_id: str | None) -> ChatResponse:
    try:
        return run_assistant(message, thread_id)
    except Exception as exc:
        return build_fallback_chat_response(message, thread_id, exc)
