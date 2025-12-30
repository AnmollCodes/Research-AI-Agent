from dotenv import load_dotenv
load_dotenv()

from typing import TypedDict, Annotated, Sequence, List, Literal, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from tools import TOOLS
import os
import json
from pydantic import BaseModel, Field

# Feature 8: Long Term Memory Load
def load_user_prefs():
    if os.path.exists("user_prefs.json"):
        with open("user_prefs.json", "r") as f:
            return json.load(f)
    return {}

USER_PREFS = load_user_prefs()
PREF_CONTEXT = f"User Preferences: {USER_PREFS}" if USER_PREFS else ""

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    mode: Literal["quick", "research", "explain"]
    plan: List[str]
    current_step: int
    research_notes: str
    review_count: int
    user_approval_needed: bool
    approval_action: Optional[str]

from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory

# LLM Setup - Switched to Gemini
# Using models/gemini-2.0-flash-exp as it is stable and fast. 
# CRITICAL: Disable safety filters to prevent "contents are required" errors on standard queries.
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash", 
    temperature=0,
    safety_settings={
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    }
)

# ----------------- PROMPTS (Updated with Feature 7) -----------------

ROUTER_PROMPT = """You are a smart router. Determine the user's intent.
Options:
- 'research': Deep dives, reports, complex plans.
- 'quick': Simple questions, chat, quick info.
- 'explain': If user asks "how do you work", "explain your graph", "who are you".

Output one of: 'research', 'quick', 'explain'.
"""

PLANNER_PROMPT = f"""You are a research planner. Break down the request into 3-5 distinct, actionable steps.
{PREF_CONTEXT}
Each step should focus on a specific aspect.
Return a valid JSON list of strings."""

EXECUTOR_PROMPT = """You are a Reasoning Research Agent.
Current Step: {step}
Context / Research Notes:
{notes}

Instructions:
1. Explain your REASONING briefly (e.g., "I need to search X because...").
2. Then select a TOOL if needed.
3. If saving notes, use the 'save_to_notes' tool and specify a relevant TOPIC.
"""

REPORTER_PROMPT = f"""You are a technical writer.
Create a final report based on the notes:
{{notes}}

{PREF_CONTEXT}
User Request: {{request}}
"""

REVIEWER_PROMPT = """Review the Agent's answer.
Check for Accuracy, Completeness, Safety.
Pass/Fail.
"""

CHAT_PROMPT = f"""You are a helpful assistant.
User Input: {{input}}
{PREF_CONTEXT}

Confidence Check:
- High confidence -> Answer.
- Low confidence -> Use Tools.
"""

EXPLAIN_PROMPT = """You are the 'Meta-Agent'.
Explain your own internal architecture to the user.
Mention:
1. Router (You)
2. Planner (Decomposes tasks)
3. Executor (Runs steps with Reasoning & Tools)
4. Validator (Checks quality)
5. Human-in-the-Loop (For sensitive actions)
"""

# ----------------- MODELS -----------------

class RoutingOutput(BaseModel):
    mode: Literal["quick", "research", "explain"]

class PlanningOutput(BaseModel):
    steps: List[str]

class ReviewOutput(BaseModel):
    status: Literal["pass", "fail"]
    feedback: str

# ----------------- NODES -----------------

import time

def safe_invoke(llm_instance, input_data, retries=3):
    last_exception = None
    for attempt in range(retries):
        try:
            return llm_instance.invoke(input_data)
        except Exception as e:
            last_exception = e
            print(f"LLM Error (Attempt {attempt+1}/{retries}): {str(e)}")
            msg = str(e).lower()
            if "429" in msg or "resourceexhausted" in msg or "quota" in msg or "contents are required" in msg or "503" in msg:
                # Exponential backoff: 2, 4, 8
                wait = 2 ** (attempt + 1)
                print(f"Rate limit/Safety hit. Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise e
    raise Exception(f"Max retries reached. Last error: {str(last_exception)}")

def router_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1].content.lower()
    
    if "explain" in last_message and "me" not in last_message:
         return {"mode": "explain"}
    
    print(f"DEBUG: Router Node Input Messages: {len(messages)}")
    for i, m in enumerate(messages):
        print(f"  Msg {i}: {type(m).__name__} - Content: {str(m.content)[:50]}...")

    structured_llm = llm.with_structured_output(RoutingOutput)
    # response = structured_llm.invoke([SystemMessage(content=ROUTER_PROMPT)] + messages)
    response = safe_invoke(structured_llm, [SystemMessage(content=ROUTER_PROMPT)] + messages)
    print(f"DEBUG: Router Response: {response}")
    
    if not response:
        print("WARNING: Router returned None. Defaulting to 'quick'.")
        return {"mode": "quick"}
        
    return {"mode": response.mode}

def planner_node(state: AgentState):
    messages = state["messages"]
    structured_llm = llm.with_structured_output(PlanningOutput)
    # response = structured_llm.invoke([SystemMessage(content=PLANNER_PROMPT)] + messages)
    response = safe_invoke(structured_llm, [SystemMessage(content=PLANNER_PROMPT)] + messages)
    return {"plan": response.steps, "current_step": 0, "research_notes": ""}

def executor_node(state: AgentState):
    plan = state["plan"]
    current_step = state.get("current_step", 0)
    notes = state.get("research_notes", "")
    step_instruction = plan[current_step]
    
    llm_executor = llm.bind_tools(TOOLS)
    prompt = EXECUTOR_PROMPT.format(step=step_instruction, notes=notes)
    
    # response = llm_executor.invoke(state["messages"] + [HumanMessage(content=prompt)])
    response = safe_invoke(llm_executor, state["messages"] + [HumanMessage(content=prompt)])
    return {"messages": [response]}

def executor_logic(state: AgentState):
    last_msg = state["messages"][-1]
    
    if last_msg.tool_calls:
        # Check if the tool is sensitive
        tool_name = last_msg.tool_calls[0]["name"]
        if tool_name == "save_to_notes":
            return "human_approval"
        return "tools"
        
    new_notes = state.get("research_notes", "") + f"\n\nStep {state['current_step']+1} Result:\n{last_msg.content}"
    return {"research_notes": new_notes, "current_step": state["current_step"] + 1}

def reporter_node(state: AgentState):
    notes = state["research_notes"]
    original_request = state["messages"][0].content
    prompt = REPORTER_PROMPT.format(notes=notes, request=original_request)
    # response = llm.invoke([HumanMessage(content=prompt)])
    response = safe_invoke(llm, [HumanMessage(content=prompt)])
    return {"messages": [response]}

def chat_node(state: AgentState):
    messages = state["messages"]
    last_user_msg = messages[-1].content
    prompt = CHAT_PROMPT.format(input=last_user_msg)
    llm_quick = llm.bind_tools(TOOLS)
    # response = llm_quick.invoke([HumanMessage(content=prompt)] + messages[:-1])
    response = safe_invoke(llm_quick, [HumanMessage(content=prompt)] + messages[:-1])
    return {"messages": [response]}

def validator_node(state: AgentState):
    last_agent_msg = state["messages"][-1].content
    structured_llm = llm.with_structured_output(ReviewOutput)
    # response = structured_llm.invoke([SystemMessage(content=REVIEWER_PROMPT + f"\nAnswer: {last_agent_msg}")])
    response = safe_invoke(structured_llm, [SystemMessage(content=REVIEWER_PROMPT + f"\nAnswer: {last_agent_msg}")])
    
    if response.status == "fail":
        return {
            "review_count": state.get("review_count", 0) + 1,
            "messages": [HumanMessage(content=f"Reviewer Feedback: {response.feedback}")]
        }
    return {"review_count": state.get("review_count", 0) + 1}

def explain_node(state: AgentState):
    # response = llm.invoke([SystemMessage(content=EXPLAIN_PROMPT)])
    response = safe_invoke(llm, [SystemMessage(content=EXPLAIN_PROMPT)])
    return {"messages": [response]}

def human_approval_node(state: AgentState):
    # This node does nothing but marks the state as needing approval is implied by logic in main.py?
    # Actually, we can just return a marker.
    pass


