# pyright: basic
from __future__ import annotations

from langgraph.graph import StateGraph, END  # type: ignore[import-untyped]
from langgraph.prebuilt import ToolNode  # type: ignore[import-untyped]
from langchain_core.messages import AIMessage  # type: ignore[import-untyped]
from typing import Any, Optional

from agent import (
    AgentState,
    router_node,
    planner_node,
    executor_node,
    executor_logic,
    reporter_node,
    chat_node,
    validator_node,
    explain_node,
    human_approval_node,
    action_planner_node,
    action_executor_node,
    action_step_manager,
    action_reporter_node,
)
from tools import TOOLS, ZAPIER_TOOLS


def create_graph(checkpointer: Optional[Any] = None) -> Any:
    graph: Any = StateGraph(AgentState)

    # ── Register all nodes ──────────────────────────────────────────────
    graph.add_node("router", router_node)
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("step_manager", executor_logic)
    graph.add_node("reporter", reporter_node)
    graph.add_node("chat_node", chat_node)
    graph.add_node("validator", validator_node)
    graph.add_node("explain_node", explain_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_node("action_planner", action_planner_node)
    graph.add_node("action_executor", action_executor_node)
    graph.add_node("action_step_manager", action_step_manager)
    graph.add_node("action_reporter", action_reporter_node)
    graph.add_node("action_tools", ToolNode(ZAPIER_TOOLS))

    # ── Entry point ─────────────────────────────────────────────────────
    graph.set_entry_point("router")

    # ── Router: branch to all four modes ────────────────────────────────
    graph.add_conditional_edges(
        "router",
        lambda state: state["mode"],  # type: ignore[arg-type]
        {
            "quick":    "chat_node",
            "research": "planner",
            "explain":  "explain_node",
            "action":   "action_planner",
        },
    )

    # ── EXPLAIN mode ────────────────────────────────────────────────────
    graph.add_edge("explain_node", END)

    # ── QUICK mode ──────────────────────────────────────────────────────
    def chat_logic(state: AgentState) -> str:  # type: ignore[type-arg]
        last: Any = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "validator"

    graph.add_conditional_edges(
        "chat_node", chat_logic,
        {"tools": "tools", "validator": "validator"},
    )

    def after_tools_logic(state: AgentState) -> str:  # type: ignore[type-arg]
        mode: str = str(state.get("mode", "quick"))
        return "chat_node" if mode == "quick" else "executor"

    graph.add_conditional_edges(
        "tools", after_tools_logic,
        {"chat_node": "chat_node", "executor": "executor"},
    )

    # ── RESEARCH mode ───────────────────────────────────────────────────
    graph.add_edge("planner", "executor")

    def executor_router(state: AgentState) -> str:  # type: ignore[type-arg]
        last: Any = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            tool_name: str = str(last.tool_calls[0]["name"])
            if tool_name == "save_to_notes":
                return "human_approval"
            return "tools"
        return "step_manager"

    graph.add_conditional_edges(
        "executor", executor_router,
        {
            "tools":          "tools",
            "human_approval": "human_approval",
            "step_manager":   "step_manager",
        },
    )

    graph.add_edge("human_approval", "tools")

    def step_router(state: AgentState) -> str:  # type: ignore[type-arg]
        current: int = int(state.get("current_step") or 0)
        total: int = len(list(state.get("plan") or []))
        return "executor" if current < total else "reporter"

    graph.add_conditional_edges(
        "step_manager", step_router,
        {"executor": "executor", "reporter": "reporter"},
    )

    # ── Validator loop ──────────────────────────────────────────────────
    def validator_logic(state: AgentState) -> str:  # type: ignore[type-arg]
        last: Any = state["messages"][-1]
        content: str = str(last.content) if hasattr(last, "content") else ""
        if "Reviewer Feedback" in content:
            mode: str = str(state.get("mode", "quick"))
            return "chat_node" if mode == "quick" else "reporter"
        return END  # type: ignore[return-value]

    graph.add_conditional_edges(
        "validator", validator_logic,
        {"chat_node": "chat_node", "reporter": "reporter", END: END},
    )

    graph.add_edge("reporter", END)

    # ── ACTION mode ─────────────────────────────────────────────────────
    graph.add_edge("action_planner", "action_executor")

    def action_executor_router(state: AgentState) -> str:  # type: ignore[type-arg]
        last: Any = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "action_tools"
        return "action_step_manager"

    graph.add_conditional_edges(
        "action_executor", action_executor_router,
        {
            "action_tools":        "action_tools",
            "action_step_manager": "action_step_manager",
        },
    )

    graph.add_edge("action_tools", "action_step_manager")

    def action_step_router(state: AgentState) -> str:  # type: ignore[type-arg]
        current: int = int(state.get("current_step") or 0)
        total: int = len(list(state.get("plan") or []))
        return "action_executor" if current < total else "action_reporter"

    graph.add_conditional_edges(
        "action_step_manager", action_step_router,
        {
            "action_executor": "action_executor",
            "action_reporter": "action_reporter",
        },
    )

    graph.add_edge("action_reporter", END)

    # ── Compile ─────────────────────────────────────────────────────────
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval"],
    )