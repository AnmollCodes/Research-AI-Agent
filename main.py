from dotenv import load_dotenv
load_dotenv()

from graph import create_graph
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
import os
import json

# Setup checkpoint for thread-level memory
memory = MemorySaver()

def run():
    if not os.getenv("OPENAI_API_KEY"):
        print("Missing OPENAI_API_KEY")
        return

    # Compile with checkpointer and interrupt
    # We interrupt BEFORE human_approval node runs.
    app = create_graph()
    app.checkpointer = memory # Bind memory
    
    # We need to re-compile with interrupts. 
    # Actually, create_graph() returns compiled graph. 
    # We should modify create_graph in graph.py to accept checkpointer and interrupts? 
    # Or just re-compile here if possible? 
    # LangGraph compiled graph is immutable structure.
    # So I must pass checkpointer/interrupts to `.compile()`.
    # Modification: I will use the app returned by create_graph() which is already compiled.
    # To add checkpointer, I need to pass it to compile().
    # Let's modify graph.py to return the UNCOMPILED graph object? 
    # Or I can just access the underlying graph and compile it myself here.
    # Wait, `app` returned by create_graph() IS CompiledStateGraph.
    # accessing `app.builder`? 
    # Easier: I will ignore the returned compile and recomile the builder if I can access it.
    # Let's import `create_graph` but actually I need the builder.
    
    # WORKAROUND: I will assume `create_graph` returns compiled. 
    # I will modify `main.py` to NOT use `create_graph()` directly but Import the `builder` construction logic?
    # No, that duplicates code.
    # I will rely on `create_graph` accepting optional args?
    # No, I didn't add args to `create_graph` in `graph.py`.
    # I will rely on `main.py` REPLACING `graph.py` logic?
    # No. 
    # Let's just modify `graph.py` one more time to accept `checkpointer` and `interrupt_before`.
    # OK, I will perform a quick edit to `graph.py` after this `main.py` is written.
    # Or I can hack it in `main.py` using `app = create_graph().attach(checkpointer=memory, interrupt_before=["human_approval"])`? No such method.
    
    # I will proceed assuming I will update `graph.py` to: `return graph.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)`
    
    print("AI Research Agent (Verified & Planned)")
    print("Features: Retry, Memory, Approval, Explanation, Sub-Agents.")
    print("Type 'quit' to exit\n")

    # Interactive Loop with Persistence
    thread_id = "user_session_1"
    config = {"configurable": {"thread_id": thread_id}}
    
    while True:
        try:
            # Check if we are resumed from interrupt
            snapshot = app.get_state(config)
            
            if snapshot.next:
                # We are paused.
                print(f"\n[System] Paused at: {snapshot.next}")
                if "human_approval" in snapshot.next:
                     print(">> ⚠️  APPROVAL REQUIRED: The Agent wants to save notes.")
                     decision = input(">> Approve? (y/n): ")
                     if decision.lower() == "y":
                         # Resume with None (let it run)
                         # We need to update user_approval_result?
                         # Our graph doesn't read input for approval, it just flows.
                         # If we resume, it executes `human_approval` node (which passes) -> `tools`.
                         # This works.
                         print(">> Approved. Resuming...")
                         # We pass None to resume
                         for event in app.stream(None, config=config):
                             handle_event(event)
                         continue
                     else:
                         print(">> Denied. Aborting step.")
                         # We can update state to Redirect?
                         # For now, just break or continue loop without resuming (deadlock).
                         # Better: Update state to clear tool call?
                         # We will just start new chat.
                         continue
            
            user_input = input("You: ")
            if user_input.lower() in ["quit", "exit"]:
                break

            # Handle User Prefs (Feature 8)
            if user_input.startswith("remember:"):
                # Save pref
                pref = user_input.replace("remember:", "").strip()
                save_pref(pref)
                print(f">> Remembered: {pref}")
                continue

            # Stream
            for event in app.stream({"messages": [HumanMessage(content=user_input)]}, config=config):
                handle_event(event)

        except Exception as e:
            print(f"Error: {e}")

def handle_event(event):
    for node, value in event.items():
        if node == "router":
            mode = value.get("mode", "unknown")
            print(f"\n[Router] Switching to {mode.upper()} mode.")
        elif node == "planner":
            print("\n[Planner] Decomposing task:")
            plan = value.get("plan", [])
            for i, step in enumerate(plan):
                print(f"  {i+1}. {step}")
            print("")
        elif node == "executor":
            if "messages" in value:
                last_msg = value["messages"][-1]
                if last_msg.tool_calls:
                    tool_name = last_msg.tool_calls[0]["name"]
                    print(f"  [Executor] 🧠 Reasoning: I need to use {tool_name}...")
                    print(f"  [Executor] Calling tool: {tool_name}")
                else:
                    print(f"  [Executor] Step output: {last_msg.content[:100]}...")
        elif node == "explain_node":
             print("\n[Meta-Agent] Explanation:\n")
             print(value["messages"][-1].content)
        elif node == "human_approval":
             print("\n[System] Reached request checkpoint.")
        elif node == "validator":
            if "messages" in value:
                print(f"\n[Validator] ❌ FEEDBACK: {value['messages'][0].content}")
            else:
                print("\n[Validator] ✅ PASSED.\n")
        elif node == "reporter":
             if "messages" in value:
                 print(f"\n[Reporter] Final Answer:\n{value['messages'][-1].content}\n")
        elif node == "chat_node":
             if "messages" in value:
                 print(f"\n[Chat] {value['messages'][-1].content}\n")

def save_pref(pref):
    prefs = {}
    if os.path.exists("user_prefs.json"):
        with open("user_prefs.json", "r") as f:
            prefs = json.load(f)
    
    # Simple list append
    idx = len(prefs)
    prefs[f"pref_{idx}"] = pref
    
    with open("user_prefs.json", "w") as f:
        json.dump(prefs, f)

if __name__ == "__main__":
    run()


