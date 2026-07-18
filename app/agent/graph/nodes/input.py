from typing import Any

from langchain_core.messages import HumanMessage

from app.agent.graph.state import AssistantState
from app.observability import observation_context, update_current_span


def latest_human_message(state: AssistantState) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return message.content
    return ""


def normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def normalize_input(state: AssistantState) -> dict[str, Any]:
    with observation_context(
        "assistant.node.normalize_input",
        as_type="agent",
        input={"thread_id": state.get("thread_id")},
    ):
        question = latest_human_message(state)
        normalized = normalize_text(question)
        update_current_span(
            output={"message_length": len(question), "normalized_length": len(normalized)},
        )
        return {
            "normalized_question": normalized,
            "warnings": [],
            "error": None,
            "error_reason": None,
            "error_details": {},
            "classification_reason": None,
            "classification_details": {},
            "planning_reason": None,
            "planning_details": {},
            "thread_id": state.get("thread_id"),
            "prompt_versions": {},
            # Reset per-turn extracted fields so stale filters from a previous
            # turn (kept by the checkpointer) never leak into a new question.
            "metric": None,
            "rank_direction": None,
            "low_metric": None,
            "high_metric": None,
            "group_by": None,
            "sort_by": None,
            "sort_dir": None,
            "metrics": None,
            "dimension": None,
            "start_date": None,
            "end_date": None,
            "vehicle_type": None,
            "vehicle_model": None,
        }
