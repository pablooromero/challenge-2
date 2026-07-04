from uuid import uuid4

from langchain_core.messages import HumanMessage

from app.agent.graph.builder import get_assistant_graph
from app.schemas.responses import ChartPayload, ChatMeta, ChatResponse, DataRange


def run_assistant(message: str, thread_id: str | None) -> ChatResponse:
    resolved_thread_id = thread_id or f"thread-{uuid4().hex[:12]}"
    graph = get_assistant_graph()
    result = graph.invoke(
        {"messages": [HumanMessage(content=message)]},
        {"configurable": {"thread_id": resolved_thread_id}},
    )

    tool_result = result.get("tool_result") or {}
    meta_payload = tool_result.get("meta", {})
    data_range_payload = meta_payload.get("data_range")
    chart_payload = result.get("chart_payload")

    return ChatResponse(
        answer=result.get("answer") or "No se pudo generar una respuesta.",
        intent=result.get("intent", "unsupported"),
        data_range=(
            DataRange.model_validate(data_range_payload) if isinstance(data_range_payload, dict) else None
        ),
        chart=ChartPayload.model_validate(chart_payload) if isinstance(chart_payload, dict) else None,
        meta=ChatMeta(
            thread_id=resolved_thread_id,
            warnings=result.get("warnings", []),
            last_data_date=data_range_payload.get("to") if isinstance(data_range_payload, dict) else None,
            source="langgraph",
        ),
    )
