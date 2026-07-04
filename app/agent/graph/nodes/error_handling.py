from typing import Literal

from langchain_core.messages import AIMessage

from app.agent.prompting import compile_prompt
from app.agent.graph.state import AssistantState
from app.observability import observation_context, update_current_span


def error_handler(state: AssistantState) -> dict:
    with observation_context(
        "assistant.node.error_handler",
        as_type="guardrail",
        input={"thread_id": state.get("thread_id")},
    ):
        raw_message = state.get("error") or "Ocurrio un error inesperado en el flujo del asistente."
        error_reason = state.get("error_reason") or "unclassified_error"
        error_details = dict(state.get("error_details", {}))
        prompt_versions = dict(state.get("prompt_versions", {}))
        warnings = list(state.get("warnings", []))

        try:
            fallback_prompt = compile_prompt("bi-assistant-fallback", message=raw_message)
            prompt_versions[fallback_prompt.name] = fallback_prompt.meta()
            message = str(fallback_prompt.compiled)
            response_source = fallback_prompt.source
        except Exception:
            message = raw_message
            response_source = "raw-fallback"

        update_current_span(
            output={"handled_error": True, "response_source": response_source},
            metadata={"error_reason": error_reason, **error_details},
            level="WARNING",
            status_message="error_handler_response",
        )
        return {
            "answer": message,
            "warnings": [*warnings, message],
            "messages": [AIMessage(content=message)],
            "chart_payload": None,
            "response_source": response_source,
            "error_reason": error_reason,
            "error_details": error_details,
            "prompt_versions": prompt_versions,
        }


def route_on_error(state: AssistantState) -> Literal["error_handler", "next"]:
    return "error_handler" if state.get("error") else "next"


def route_after_planning(state: AssistantState) -> Literal["error_handler", "execute_tools"]:
    return "error_handler" if state.get("error") else "execute_tools"
