from uuid import uuid4

from langchain_core.messages import HumanMessage

from app.agent.graph.builder import get_assistant_graph
from app.core.config import get_settings
from app.observability import (
    get_current_trace_details,
    observation_context,
    propagation_context,
    set_trace_io,
    update_current_span,
)
from app.schemas.responses import ChartPayload, ChatMeta, ChatResponse, DataRange, DecisionMeta, PromptMeta


def run_assistant(message: str, thread_id: str | None) -> ChatResponse:
    resolved_thread_id = thread_id or f"thread-{uuid4().hex[:12]}"
    settings = get_settings()

    with observation_context(
        "assistant.chat.request",
        as_type="chain",
        input={"message": message, "thread_id": resolved_thread_id},
        metadata={"feature": "chat", "transport": "fastapi"},
    ):
        with propagation_context(
            session_id=resolved_thread_id,
            metadata={"feature": "chat", "threadId": resolved_thread_id, "transport": "fastapi"},
            version="assistant-v1",
            tags=["bi-assistant", "feature:chat", f"env:{settings.app_env}"],
            trace_name="assistant.chat.request",
            environment=settings.app_env,
        ):
            graph = get_assistant_graph()
            with observation_context(
                "assistant.graph.invoke",
                as_type="agent",
                input={"thread_id": resolved_thread_id},
            ):
                result = graph.invoke(
                    {"messages": [HumanMessage(content=message)], "thread_id": resolved_thread_id},
                    {"configurable": {"thread_id": resolved_thread_id}},
                )

            tool_result = result.get("tool_result") or {}
            meta_payload = tool_result.get("meta", {})
            data_range_payload = meta_payload.get("data_range")
            chart_payload = result.get("chart_payload")
            prompt_versions = result.get("prompt_versions") or {}

            response = ChatResponse(
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
                    source=(
                        f"langgraph-{result.get('response_source') or result.get('classification_source')}"
                        if result.get("response_source") or result.get("classification_source")
                        else "langgraph"
                    ),
                    model=result.get("llm_model"),
                    prompts=[
                        PromptMeta.model_validate(prompt_info)
                        for prompt_info in prompt_versions.values()
                        if isinstance(prompt_info, dict)
                    ],
                    decisions=DecisionMeta(
                        classification_source=result.get("classification_source"),
                        classification_reason=result.get("classification_reason"),
                        planning_reason=result.get("planning_reason"),
                        error_reason=result.get("error_reason"),
                    ),
                ),
            )

            set_trace_io(
                input={"message": message, "thread_id": resolved_thread_id},
                output={"intent": response.intent, "answer": response.answer},
            )
            update_current_span(
                output={
                    "intent": response.intent,
                    "warnings_count": len(response.meta.warnings),
                    "prompt_count": len(response.meta.prompts),
                },
                metadata={
                    "thread_id": resolved_thread_id,
                    "intent": response.intent,
                    "model": response.meta.model,
                    "prompt_names": [prompt.name for prompt in response.meta.prompts],
                    "classification_source": result.get("classification_source"),
                    "classification_reason": result.get("classification_reason"),
                    "response_source": result.get("response_source"),
                    "planning_reason": result.get("planning_reason"),
                    "error_reason": result.get("error_reason"),
                    "data_range_from": data_range_payload.get("from") if isinstance(data_range_payload, dict) else None,
                    "data_range_to": data_range_payload.get("to") if isinstance(data_range_payload, dict) else None,
                },
            )
            trace_id, trace_url = get_current_trace_details()
            response.meta.trace_id = trace_id
            response.meta.trace_url = trace_url

    return response
