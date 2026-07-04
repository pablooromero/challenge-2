from functools import lru_cache

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import RetryPolicy

from app.graph.nodes import (
    build_chart_payload,
    classify_intent_and_entities,
    compose_answer,
    error_handler,
    normalize_input,
    plan_tools,
    resolve_context,
    route_after_planning,
    route_on_error,
)
from app.graph.state import AssistantState
from app.tools import get_all_tools


@lru_cache
def get_assistant_graph():
    builder = StateGraph(AssistantState)
    checkpointer = InMemorySaver()

    tool_node = ToolNode(get_all_tools())

    builder.add_node("normalize_input", normalize_input)
    builder.add_node("classify_intent_and_entities", classify_intent_and_entities)
    builder.add_node("resolve_context", resolve_context)
    builder.add_node("plan_tools", plan_tools)
    builder.add_node(
        "execute_tools",
        tool_node,
        retry=RetryPolicy(max_attempts=2, initial_interval=0.5),
    )
    builder.add_node("compose_answer", compose_answer)
    builder.add_node("build_chart_payload", build_chart_payload)
    builder.add_node("error_handler", error_handler)

    builder.add_edge(START, "normalize_input")
    builder.add_conditional_edges(
        "normalize_input",
        route_on_error,
        {"next": "classify_intent_and_entities", "error_handler": "error_handler"},
    )
    builder.add_conditional_edges(
        "classify_intent_and_entities",
        route_on_error,
        {"next": "resolve_context", "error_handler": "error_handler"},
    )
    builder.add_conditional_edges(
        "resolve_context",
        route_on_error,
        {"next": "plan_tools", "error_handler": "error_handler"},
    )
    builder.add_conditional_edges(
        "plan_tools",
        route_after_planning,
        {"execute_tools": "execute_tools", "error_handler": "error_handler"},
    )
    builder.add_edge("execute_tools", "compose_answer")
    builder.add_conditional_edges(
        "compose_answer",
        route_on_error,
        {"next": "build_chart_payload", "error_handler": "error_handler"},
    )
    builder.add_edge("build_chart_payload", END)
    builder.add_edge("error_handler", END)

    return builder.compile(checkpointer=checkpointer)
