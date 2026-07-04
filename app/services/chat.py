from uuid import uuid4

from app.schemas.responses import ChatMeta, ChatResponse, DataRange


def build_mock_chat_response(message: str, thread_id: str | None) -> ChatResponse:
    resolved_thread_id = thread_id or f"thread-{uuid4().hex[:12]}"
    prompt_hint = message[:80]

    return ChatResponse(
        answer=(
            "La capa HTTP ya esta lista y esta respuesta es temporal. "
            "En la siguiente fase vamos a reemplazar este mock por consultas reales a MySQL."
        ),
        intent="mock_response",
        data_range=DataRange(from_date=None, to_date=None),
        meta=ChatMeta(
            thread_id=resolved_thread_id,
            warnings=[
                "Aun no hay integracion con base de datos.",
                f"Ultima consulta recibida: {prompt_hint}",
            ],
            last_data_date=None,
            source="mock",
        ),
    )
