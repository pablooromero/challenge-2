from app.schemas.responses import ChatResponse
from app.services.assistant import run_assistant


def build_chat_response(message: str, thread_id: str | None) -> ChatResponse:
    return run_assistant(message, thread_id)
