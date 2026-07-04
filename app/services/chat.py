from app.agent.assistant import run_assistant
from app.schemas.responses import ChatResponse


def build_chat_response(message: str, thread_id: str | None) -> ChatResponse:
    return run_assistant(message, thread_id)
