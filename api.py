# pyright: basic
from __future__ import annotations

from dotenv import load_dotenv  # type: ignore[import-untyped]
load_dotenv()

from fastapi import FastAPI  # type: ignore[import-untyped]
from fastapi.responses import StreamingResponse  # type: ignore[import-untyped]
from fastapi.middleware.cors import CORSMiddleware  # type: ignore[import-untyped]
from pydantic import BaseModel  # type: ignore[import-untyped]
from typing import Any, Dict, List, Optional, AsyncGenerator
from langchain_core.messages import HumanMessage  # type: ignore[import-untyped]
from langgraph.checkpoint.memory import MemorySaver  # type: ignore[import-untyped]
from graph import create_graph
import uvicorn  # type: ignore[import-untyped]
import json

app: Any = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory: Any = MemorySaver()
agent_app: Any = create_graph(checkpointer=memory)


class ChatRequest(BaseModel):  # type: ignore[misc]
    message: str
    thread_id: str = "default_thread"
    mode: Optional[str] = None


class ApprovalRequest(BaseModel):  # type: ignore[misc]
    thread_id: str
    approved: bool


@app.get("/")  # type: ignore[misc]
def read_root() -> Dict[str, str]:
    return {"status": "ISEA v3.0 API running"}


def process_event(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert LangGraph stream events to frontend-friendly JSON."""
    events_out: List[Dict[str, Any]] = []

    for node, value in event.items():
        if str(node).startswith("__"):
            continue

        data: Dict[str, Any] = {}
        node_str: str = str(node)

        if node_str == "router":
            data["mode"] = value.get("mode")

        elif node_str == "planner":
            data["plan"] = value.get("plan", [])

        elif node_str == "executor":
            msgs: List[Any] = value.get("messages", [])
            if msgs:
                last: Any = msgs[-1]
                tool_calls: Any = getattr(last, "tool_calls", None)
                if tool_calls:
                    data["tool"] = str(tool_calls[0]["name"])
                    data["reasoning"] = f"Using tool: {tool_calls[0]['name']}"
                else:
                    data["output"] = str(last.content)

        elif node_str == "step_manager":
            data["status"] = "step_completed"

        elif node_str == "reporter":
            msgs = value.get("messages", [])
            if msgs:
                data["final_response"] = str(msgs[-1].content)

        elif node_str == "chat_node":
            msgs = value.get("messages", [])
            if msgs:
                data["response"] = str(msgs[-1].content)

        elif node_str == "validator":
            msgs = value.get("messages", [])
            if msgs:
                data["feedback"] = str(msgs[0].content)
                data["status"] = "failed"
            else:
                data["status"] = "passed"

        elif node_str == "human_approval":
            data["status"] = "awaiting_approval"
            data["message"] = "Agent wants to save notes. Approve or reject."

        elif node_str == "explain_node":
            msgs = value.get("messages", [])
            if msgs:
                content: str = str(msgs[-1].content)
                data["explanation"] = content
                data["response"] = content

        elif node_str == "tools":
            data["status"] = "tool_executed"

        elif node_str == "action_planner":
            data["action_plan"] = value.get("plan", [])
            data["mode"] = "action"

        elif node_str == "action_executor":
            msgs = value.get("messages", [])
            if msgs:
                last = msgs[-1]
                tool_calls = getattr(last, "tool_calls", None)
                if tool_calls:
                    args: Dict[str, Any] = tool_calls[0].get("args", {})
                    data["zapier_action"] = str(args.get("action", "?"))
                    data["status"] = "executing"
                else:
                    data["output"] = str(last.content)

        elif node_str == "action_tools":
            msgs = value.get("messages", [])
            if msgs:
                data["tool_result"] = str(msgs[-1].content)
                data["status"] = "action_executed"

        elif node_str == "action_step_manager":
            data["status"] = "step_completed"
            data["current_step"] = value.get("current_step", 0)

        elif node_str == "action_reporter":
            msgs = value.get("messages", [])
            if msgs:
                final: str = str(msgs[-1].content)
                data["final_response"] = final
                data["response"] = final
                data["status"] = "action_complete"

        events_out.append({"node": node_str, "data": data})

    return events_out


@app.post("/chat")  # type: ignore[misc]
async def chat_endpoint(req: ChatRequest) -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        config: Dict[str, Any] = {"configurable": {"thread_id": req.thread_id}}

        snapshot: Any = agent_app.get_state(config)
        if snapshot.next:
            yield json.dumps({
                "events": [{
                    "node": "system",
                    "data": {
                        "status": "paused",
                        "message": "Agent is waiting for approval.",
                        "next_step": list(snapshot.next)
                    }
                }]
            }) + "\n"
            return

        print(f"[API] /chat thread={req.thread_id} msg={req.message[:60]}")
        input_msg: Any = HumanMessage(content=req.message)

        try:
            for event in agent_app.stream(
                {"messages": [input_msg]},
                config=config
            ):
                processed: List[Dict[str, Any]] = process_event(event)
                if processed:
                    yield json.dumps({"events": processed}) + "\n"

            final_snap: Any = agent_app.get_state(config)
            if final_snap.next:
                yield json.dumps({
                    "status": "paused",
                    "events": [{
                        "node": "human_approval",
                        "data": {"status": "paused"}
                    }]
                }) + "\n"

        except Exception as exc:
            print(f"[API] Error: {exc}")
            yield json.dumps({"status": "error", "message": str(exc)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@app.post("/approve")  # type: ignore[misc]
async def approve_endpoint(req: ApprovalRequest) -> StreamingResponse:
    async def resume_generator() -> AsyncGenerator[str, None]:
        config: Dict[str, Any] = {"configurable": {"thread_id": req.thread_id}}
        snapshot: Any = agent_app.get_state(config)

        if not snapshot.next:
            yield json.dumps({"status": "error", "message": "No pending approval."}) + "\n"
            return

        if req.approved:
            try:
                for event in agent_app.stream(None, config=config):
                    processed: List[Dict[str, Any]] = process_event(event)
                    if processed:
                        yield json.dumps({"events": processed}) + "\n"
            except Exception as exc:
                yield json.dumps({"status": "error", "message": str(exc)}) + "\n"
        else:
            yield json.dumps({"status": "cancelled", "message": "Step rejected."}) + "\n"

    return StreamingResponse(resume_generator(), media_type="application/x-ndjson")


@app.get("/state/{thread_id}")  # type: ignore[misc]
async def get_state(thread_id: str) -> Dict[str, Any]:
    config: Dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot: Any = agent_app.get_state(config)
        return {
            "thread_id": thread_id,
            "next": list(snapshot.next) if snapshot.next else [],
            "mode": snapshot.values.get("mode"),
        }
    except Exception as exc:
        return {"error": str(exc)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)