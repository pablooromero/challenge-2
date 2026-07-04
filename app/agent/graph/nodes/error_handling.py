from typing import Literal

from langchain_core.messages import AIMessage

from app.agent.graph.state import AssistantState


def error_handler(state: AssistantState) -> dict:
    message = state.get("error") or "Ocurrio un error inesperado en el flujo del asistente."
    return {
        "answer": message,
        "warnings": [message],
        "messages": [AIMessage(content=message)],
        "chart_payload": None,
    }


def route_on_error(state: AssistantState) -> Literal["error_handler", "next"]:
    return "error_handler" if state.get("error") else "next"


def route_after_planning(state: AssistantState) -> Literal["error_handler", "execute_tools"]:
    return "error_handler" if state.get("error") else "execute_tools"
