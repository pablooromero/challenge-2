from typing import Any

from langchain_core.messages import HumanMessage

from app.agent.graph.state import AssistantState


def latest_human_message(state: AssistantState) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return message.content
    return ""


def normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def normalize_input(state: AssistantState) -> dict[str, Any]:
    question = latest_human_message(state)
    normalized = normalize_text(question)
    return {
        "normalized_question": normalized,
        "warnings": [],
        "error": None,
    }
