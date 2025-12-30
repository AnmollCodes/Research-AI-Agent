from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
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
    human_approval_node
)
from tools import TOOLS

def create_graph(checkpointer=None):
    graph = StateGraph(AgentState)

    # Add Nodes
    graph.add_node("router", router_node)
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("reporter", reporter_node)
    graph.add_node("chat_node", chat_node)
    graph.add_node("validator", validator_node)
    graph.add_node("explain_node", explain_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("tools", ToolNode(TOOLS))
    
    # "step_manager" alias for executor logic
    graph.add_node("step_manager", executor_logic)

    # Set Entry Point
    graph.set_entry_point("router")

    # Routing Logic
    graph.add_conditional_edges(
        "router",
        lambda state: state["mode"],
        {
            "quick": "chat_node",
            "research": "planner",
            "explain": "explain_node"
        }
    )

    # EXPLAIN Mode
    graph.add_edge("explain_node", END)

    # QUICK Mode
    def chat_logic(state):
        last = state["messages"][-1]
        if last.tool_calls:
            return "tools"
        return "validator"

    graph.add_conditional_edges("chat_node", chat_logic, {"tools": "tools", "validator": "validator"})
    
    def after_tools_logic(state):
        if state["mode"] == "quick":
            return "chat_node"
        else:
            return "executor"

    graph.add_conditional_edges("tools", after_tools_logic, {"chat_node": "chat_node", "executor": "executor"})
    
    # RESEARCH Mode
    graph.add_edge("planner", "executor")
    
    def executor_router(state):
        last = state["messages"][-1]
        if last.tool_calls:
            if last.tool_calls[0]["name"] == "save_to_notes":
                return "human_approval"
            return "tools"
        return "step_manager"

    graph.add_conditional_edges(
        "executor",
        executor_router,
        {
            "tools": "tools",
            "human_approval": "human_approval",
            "step_manager": "step_manager"
        }
    )
    
    graph.add_edge("human_approval", "tools")
    
    graph.add_conditional_edges(
        "step_manager",
        lambda state: "executor" if state["current_step"] < len(state["plan"]) else "reporter",
        {"executor": "executor", "reporter": "reporter"}
    )
    
    # Validator Loop
    def validator_logic(state):
        last = state["messages"][-1]
        if "Reviewer Feedback" in last.content:
            return "chat_node" if state["mode"] == "quick" else "reporter"
        return END

    graph.add_conditional_edges("validator", validator_logic, {"chat_node": "chat_node", "reporter": "reporter", END: END})

    return graph.compile(checkpointer=checkpointer, interrupt_before=["human_approval"])



