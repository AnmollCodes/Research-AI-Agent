from agent import AgentState, router_node, planner_node, llm
from langchain_core.messages import HumanMessage
from graph import create_graph

print("Testing simple LLM invocation...")
try:
    msg = llm.invoke("Hi")
    print(f"LLM Response: {msg.content}")
except Exception as e:
    print(f"LLM Invocation Failed: {e}")

print("\nTesting Router Node...")
state = {"messages": [HumanMessage(content="Result the latest AI")]}
try:
    res = router_node(state)
    print(f"Router Output: {res}")
except Exception as e:
    print(f"Router Failed: {e}")

print("\nTesting Planner Node...")
try:
    res = planner_node(state)
    print(f"Planner Output: {res}")
except Exception as e:
    print(f"Planner Failed: {e}")

print("\nTesting Chat Node...")
try:
    from agent import chat_node, llm, CHAT_PROMPT
    msg = HumanMessage(content="Hello")
    state_msgs = [msg]
    last_user_msg = "Hello"
    prompt = CHAT_PROMPT.format(input=last_user_msg)
    input_list = [HumanMessage(content=prompt)] + state_msgs[:-1]
    
except Exception as e:
    print(f"Chat Node Failed: {e}")

print("\nTesting Tool Binding...")
try:
    from agent import llm
    from tools import TOOLS
    llm_with_tools = llm.bind_tools(TOOLS)
    res = llm_with_tools.invoke([HumanMessage(content="What is 55 * 3?")])
    print(f"Tool Binding Result: {res}")
except Exception as e:
    print(f"Tool Binding Failed: {e}")

print("\nTesting Full Graph...")
try:
    app = create_graph()
    for event in app.stream(state):
        print(f"Event: {event}")
except Exception as e:
    print(f"Graph Failed: {e}")
