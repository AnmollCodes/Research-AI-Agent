# pyright: basic
from __future__ import annotations

from dotenv import load_dotenv  # type: ignore[import-untyped]
load_dotenv()

import os
import json
import time
from typing import Any, Dict, List, Literal, Optional, Sequence

from langchain_google_genai import (  # type: ignore[import-untyped]
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)
from langchain_core.messages import (  # type: ignore[import-untyped]
    BaseMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
)
from langgraph.graph.message import add_messages  # type: ignore[import-untyped]
from typing_extensions import Annotated, TypedDict
from pydantic import BaseModel  # type: ignore[import-untyped]

from tools import TOOLS, ZAPIER_TOOLS


def load_user_prefs() -> Dict[str, Any]:
    if os.path.exists("user_prefs.json"):
        with open("user_prefs.json", "r") as f:
            data: Dict[str, Any] = json.load(f)
            return data
    return {}


USER_PREFS: Dict[str, Any] = load_user_prefs()
PREF_CONTEXT: str = f"User Preferences: {USER_PREFS}" if USER_PREFS else ""


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    mode: Literal["quick", "research", "explain", "action"]
    plan: List[str]
    current_step: int
    research_notes: str
    review_count: int
    user_approval_needed: bool
    approval_action: Optional[str]
    action_results: Optional[List[str]]


llm: Any = ChatGoogleGenerativeAI(  # type: ignore[call-arg]
    model="gemini-2.0-flash-lite",   # ← was gemini-2.0-flash. Lite = 30 RPM free vs 15 RPM
    temperature=0,
    safety_settings={
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    },
)

ROUTER_PROMPT = """You are a smart router. Classify the user's intent into exactly one of:

- 'research'  : Deep dives, analysis, reports, complex multi-step questions.
- 'quick'     : Simple questions, greetings, quick facts, conversational replies.
- 'explain'   : User asks how you work, about your architecture, who you are.
- 'action'    : User wants to DO something in the real world.
                Examples: reschedule a meeting, send an email, message Slack,
                create a calendar event, notify attendees.

Reply with exactly one word: research | quick | explain | action
"""

PLANNER_PROMPT: str = f"""You are a research planner. Break the request into 2 to 3
distinct, actionable research steps.
{PREF_CONTEXT}
Each step must focus on a specific aspect. Return a valid JSON list of strings only.
"""

EXECUTOR_PROMPT = """You are a Reasoning Research Agent.

Current Step: {step}
Research Notes So Far:
{notes}

Instructions:
1. Briefly explain your REASONING (why this step matters).
2. Use search_web if you need current information.
3. Use save_to_notes to record important findings (provide a topic name).
4. If no tool needed, provide your analysis directly.
"""

REPORTER_PROMPT: str = f"""You are a technical writer. Produce a comprehensive final report.

Research Notes:
{{notes}}

{PREF_CONTEXT}
Original Request: {{request}}

Write the report in clear sections. Be specific and cite findings from the notes.
"""

REVIEWER_PROMPT = """You are a quality reviewer. Evaluate the following answer.

Check for:
- Accuracy: are the facts correct?
- Completeness: does it fully address the request?
- Clarity: is it well structured?

Answer: {answer}

Reply with status (pass or fail) and brief feedback.
"""

CHAT_PROMPT: str = f"""You are a helpful, concise assistant.
{PREF_CONTEXT}

User Input: {{input}}

If confident, respond directly. If you need current info, use search_web.
"""

EXPLAIN_PROMPT = """You are the Meta-Agent. Explain your own architecture clearly.

ISEA v3.0 components:
1. Router       - classifies intent: quick | research | explain | action
2. Planner      - decomposes research tasks into 3-5 steps
3. Executor     - runs each step, calls tools (web search, notes, calculator)
4. Validator    - checks answer quality, triggers retry if it fails
5. Reporter     - synthesises research notes into a final report
6. HITL Safety  - pauses for human approval before sensitive write operations
7. Action Mode  - NEW: executes real-world tasks via Zapier SDK:
   - Reschedule Google Calendar meetings
   - Send emails via Gmail
   - Post messages to Slack
   - Create calendar events
"""

ACTION_PLANNER_PROMPT = """You are an action planner. The user wants to perform a real-world task.

Available Zapier actions:
- reschedule-meeting : find a calendar event, move it, notify Slack
- send-email         : send an email via Gmail
- create-event       : create a Google Calendar event
- slack-message      : post a message to a Slack channel

Produce a concise 2-4 step plan. Return ONLY a valid JSON list of strings.
Example: ["Check connected apps", "Reschedule standup to Thursday 10am", "Notify #engineering"]
"""

ACTION_EXECUTOR_PROMPT = """You are an action execution agent.

Current Step: {step}
Steps Completed: {results}
Original Request: {request}

Instructions:
1. Use zapier_execute to perform the action in the current step.
2. If unsure which apps are connected, call list_zapier_connections first.
3. When calling zapier_execute, provide:
   - action: one of reschedule-meeting | send-email | create-event | slack-message
   - params: a valid JSON string with all required fields
4. All datetimes must be ISO 8601: 2026-04-20T10:00:00-00:00
5. If a detail is missing, make a reasonable assumption and state it.
"""

ACTION_REPORTER_PROMPT = """You are a helpful assistant summarising completed actions.

Original request: {request}

Actions completed:
{results}

Write a friendly, clear summary of what was done, what changed, and who was notified.
"""


class RoutingOutput(BaseModel):  # type: ignore[misc]
    mode: Literal["quick", "research", "explain", "action"]


class PlanningOutput(BaseModel):  # type: ignore[misc]
    steps: List[str]


class ReviewOutput(BaseModel):  # type: ignore[misc]
    status: Literal["pass", "fail"]
    feedback: str


def safe_invoke(llm_instance: Any, input_data: Any, retries: int = 3) -> Any:
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(retries):
        try:
            return llm_instance.invoke(input_data)
        except Exception as exc:
            last_exc = exc
            msg: str = str(exc).lower()
            print(f"LLM Error (attempt {attempt + 1}/{retries}): {exc}")
            if any(
                kw in msg
                for kw in ("429", "resourceexhausted", "quota",
                           "contents are required", "503")
            ):
                wait: int = 2 ** (attempt + 1)
                print(f"Rate limit hit. Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise exc
    raise RuntimeError(f"Max retries reached. Last error: {last_exc}")


def _msgs(state: AgentState) -> List[BaseMessage]:
    return list(state["messages"])


def router_node(state: AgentState) -> Dict[str, Any]:
    messages: List[BaseMessage] = _msgs(state)
    last_content: str = str(messages[-1].content).lower()
    if "explain" in last_content and "me" not in last_content:
        return {"mode": "explain"}
    print(f"DEBUG router: {len(messages)} message(s)")
    structured_llm: Any = llm.with_structured_output(RoutingOutput)
    response: Any = safe_invoke(
        structured_llm, [SystemMessage(content=ROUTER_PROMPT), *messages]
    )
    print(f"DEBUG router response: {response}")
    if response is None:
        return {"mode": "quick"}
    return {"mode": response.mode}


def planner_node(state: AgentState) -> Dict[str, Any]:
    messages: List[BaseMessage] = _msgs(state)
    structured_llm: Any = llm.with_structured_output(PlanningOutput)
    response: Any = safe_invoke(
        structured_llm, [SystemMessage(content=PLANNER_PROMPT), *messages]
    )
    return {"plan": response.steps, "current_step": 0, "research_notes": ""}


def executor_node(state: AgentState) -> Dict[str, Any]:
    plan: List[str] = list(state.get("plan") or [])
    current_step: int = int(state.get("current_step") or 0)
    notes: str = str(state.get("research_notes") or "")
    step_instruction: str = plan[current_step]
    llm_executor: Any = llm.bind_tools(TOOLS)
    prompt: str = EXECUTOR_PROMPT.format(step=step_instruction, notes=notes)
    response: Any = safe_invoke(
        llm_executor, [*_msgs(state), HumanMessage(content=prompt)]
    )
    return {"messages": [response]}


def executor_logic(state: AgentState) -> Dict[str, Any]:
    last_msg: BaseMessage = _msgs(state)[-1]
    current: int = int(state.get("current_step") or 0)
    notes: str = str(state.get("research_notes") or "")
    new_notes: str = notes + f"\n\nStep {current + 1} Result:\n{str(last_msg.content)}"
    return {"research_notes": new_notes, "current_step": current + 1}


def reporter_node(state: AgentState) -> Dict[str, Any]:
    notes: str = str(state.get("research_notes") or "")
    original_request: str = str(_msgs(state)[0].content)
    prompt: str = REPORTER_PROMPT.format(notes=notes, request=original_request)
    response: Any = safe_invoke(llm, [HumanMessage(content=prompt)])
    return {"messages": [response]}


def chat_node(state: AgentState) -> Dict[str, Any]:
    messages: List[BaseMessage] = _msgs(state)
    last_user_msg: str = str(messages[-1].content)
    prompt: str = CHAT_PROMPT.format(input=last_user_msg)
    llm_quick: Any = llm.bind_tools(TOOLS)
    response: Any = safe_invoke(
        llm_quick, [HumanMessage(content=prompt), *messages[:-1]]
    )
    return {"messages": [response]}


def validator_node(state: AgentState) -> Dict[str, Any]:
    last_content: str = str(_msgs(state)[-1].content)
    structured_llm: Any = llm.with_structured_output(ReviewOutput)
    response: Any = safe_invoke(
        structured_llm,
        [SystemMessage(content=REVIEWER_PROMPT.format(answer=last_content))],
    )
    review_count: int = int(state.get("review_count") or 0) + 1
    if response is not None and str(response.status) == "fail":
        return {
            "review_count": review_count,
            "messages": [HumanMessage(content=f"Reviewer Feedback: {response.feedback}")],
        }
    return {"review_count": review_count}


def explain_node(state: AgentState) -> Dict[str, Any]:
    response: Any = safe_invoke(llm, [SystemMessage(content=EXPLAIN_PROMPT)])
    return {"messages": [response]}


def human_approval_node(state: AgentState) -> None:
    return None


def action_planner_node(state: AgentState) -> Dict[str, Any]:
    messages: List[BaseMessage] = _msgs(state)
    structured_llm: Any = llm.with_structured_output(PlanningOutput)
    response: Any = safe_invoke(
        structured_llm, [SystemMessage(content=ACTION_PLANNER_PROMPT), *messages]
    )
    steps: List[str] = response.steps if response else ["Execute the requested action"]
    print(f"DEBUG action plan: {steps}")
    return {"plan": steps, "current_step": 0, "action_results": []}


def action_executor_node(state: AgentState) -> Dict[str, Any]:
    plan: List[str] = list(state.get("plan") or [])
    current_step: int = int(state.get("current_step") or 0)
    raw_results: Optional[List[str]] = state.get("action_results")
    results: List[str] = list(raw_results) if raw_results else []
    original_request: str = str(_msgs(state)[0].content)
    step_instruction: str = plan[current_step]
    results_text: str = "\n".join(results) if results else "None yet"
    prompt: str = ACTION_EXECUTOR_PROMPT.format(
        step=step_instruction, results=results_text, request=original_request
    )
    llm_action: Any = llm.bind_tools(ZAPIER_TOOLS)
    response: Any = safe_invoke(
        llm_action, [SystemMessage(content=prompt), *_msgs(state)]
    )
    return {"messages": [response]}


def action_step_manager(state: AgentState) -> Dict[str, Any]:
    last_msg: BaseMessage = _msgs(state)[-1]
    current_step: int = int(state.get("current_step") or 0)
    raw_results: Optional[List[str]] = state.get("action_results")
    results: List[str] = list(raw_results) if raw_results else []
    results.append(f"Step {current_step + 1}: {str(last_msg.content)}")
    return {"action_results": results, "current_step": current_step + 1}


def action_reporter_node(state: AgentState) -> Dict[str, Any]:
    raw_results: Optional[List[str]] = state.get("action_results")
    results: List[str] = list(raw_results) if raw_results else []
    original_request: str = str(_msgs(state)[0].content)
    results_text: str = "\n".join(results) if results else "No actions were completed."
    prompt: str = ACTION_REPORTER_PROMPT.format(
        request=original_request, results=results_text
    )
    response: Any = safe_invoke(llm, [HumanMessage(content=prompt)])
    return {"messages": [response]}