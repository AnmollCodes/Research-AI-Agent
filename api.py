from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Any
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from graph import create_graph
import uvicorn
import os
import json
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for thread state (simulating per-user persistence)
memory = MemorySaver()

# Initialize Graph
agent_app = create_graph(checkpointer=memory)

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default_thread"
    mode: Optional[str] = None 

class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool

@app.get("/")
def read_root():
    return {"status": "Agent API is running"}

def process_event(event):
    """Refactored helper to process a single event and yield JSON string."""
    events_out = []
    
    for node, value in event.items():
        event_data = {"node": node, "data": {}}
        
        if node == "router":
            event_data["data"]["mode"] = value.get("mode")
        elif node == "planner":
            event_data["data"]["plan"] = value.get("plan")
        elif node == "executor":
            msgs = value.get("messages", [])
            if msgs:
                last = msgs[-1]
                if last.tool_calls:
                    event_data["data"]["tool"] = last.tool_calls[0]["name"]
                    event_data["data"]["reasoning"] = f"Reasoning: using {last.tool_calls[0]['name']}..."
                else:
                    event_data["data"]["output"] = last.content
        elif node == "step_manager":
            event_data["data"]["status"] = "step_completed"
        elif node == "reporter":
            if "messages" in value:
                event_data["data"]["final_response"] = value["messages"][-1].content
        elif node == "chat_node":
            if "messages" in value:
                event_data["data"]["response"] = value["messages"][-1].content
        elif node == "validator":
            if "messages" in value:
                    event_data["data"]["feedback"] = value["messages"][0].content
                    event_data["data"]["status"] = "failed"
            else:
                    event_data["data"]["status"] = "passed"
        elif node == "human_approval":
            event_data["data"]["status"] = "awaiting_approval"
        elif node == "explain_node":
                if "messages" in value:
                #    event_data["data"]["explanation"] = value["messages"][-1].content
                   event_data["data"]["explanation"] = value["messages"][-1].content

        events_out.append(event_data)
        
    return events_out

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    async def event_generator():
        config = {"configurable": {"thread_id": req.thread_id}}
        
        # Check for interrupts first
        # We need to do this carefully. If we just get state, we might see 'next'.
        snapshot = agent_app.get_state(config)
        if snapshot.next:
            yield json.dumps({
                "events": [{
                    "node": "system", 
                    "data": {
                        "status": "paused", 
                        "message": "Agent is waiting for approval.", 
                        "next_step": snapshot.next
                    }
                }]
            }) + "\n"
            return

        print(f"Received message: {req.message} Thread: {req.thread_id}")
        input_msg = HumanMessage(content=req.message)
        
        try:
             # Using asyncio.to_thread to not block the event loop while the sync graph runs
             # However, we need to yield events AS they come.
             # Since 'stream' is a generator, we can iterate it. 
             # To play nice with async FastAPI, we can assume stream is fast enough or just run it.
             # For a truly non-blocking experience with sync code, we'd need to run the whole stream in a thread and push to a queue, but that's complex.
             # Given this is a local demo, iterating the sync generator directly in this async def 
             # will block the loop for the duration of each step. That's acceptable for single-user.
             
            for event in agent_app.stream({"messages": [input_msg]}, config=config):
                 processed_events = process_event(event) # returns list
                 if processed_events:
                     # yield structure compatible with frontend
                     yield json.dumps({"events": processed_events}) + "\n"
                     
            # Check final state for pause
            final_snap = agent_app.get_state(config)
            if final_snap.next:
                 yield json.dumps({"status": "paused", "events": [{"node": "human_approval", "data": {"status": "paused"}}]}) + "\n"

        except Exception as e:
            yield json.dumps({"status": "error", "message": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.post("/approve")
async def approve_endpoint(req: ApprovalRequest):
    async def resume_generator():
        config = {"configurable": {"thread_id": req.thread_id}}
        snapshot = agent_app.get_state(config)
        
        if not snapshot.next:
            yield json.dumps({"status": "error", "message": "No pending approval found."}) + "\n"
            return
        
        if req.approved:
            try:
                # Resume
                # Passing None to stream resumes from interruption
                for event in agent_app.stream(None, config=config):
                    processed_events = process_event(event)
                    if processed_events:
                        yield json.dumps({"events": processed_events}) + "\n"
            except Exception as e:
                yield json.dumps({"status": "error", "message": str(e)}) + "\n"
        else:
             yield json.dumps({"status": "cancelled", "message": "Step denied."}) + "\n"
             
    return StreamingResponse(resume_generator(), media_type="application/x-ndjson")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
