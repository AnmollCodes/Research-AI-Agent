# pyright: basic
from __future__ import annotations

from langchain.tools import tool  # type: ignore[import-untyped]
from datetime import datetime
import os
import time
import json
import requests
from typing import Any, Callable, List, Optional
from dotenv import load_dotenv  # type: ignore[import-untyped]
from tavily import TavilyClient  # type: ignore[import-untyped]

load_dotenv()

_TAVILY_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")
tavily: Optional[Any] = TavilyClient(api_key=_TAVILY_KEY) if _TAVILY_KEY else None
ZAPIER_SERVICE_URL: str = os.getenv("ZAPIER_SERVICE_URL", "http://localhost:3001")


def retry_operation(
    func: Callable[[], str],
    retries: int = 3,
    delay: int = 1,
) -> str:
    """Retry a zero-arg callable up to `retries` times with a fixed delay."""
    last_error: str = "Unknown error"
    for attempt in range(retries):
        try:
            result: str = func()
            return result
        except Exception as exc:
            last_error = str(exc)
            if attempt < retries - 1:
                time.sleep(delay)
    return f"Error after {retries} retries: {last_error}"


@tool  # type: ignore[misc]
def search_web(query: str) -> str:
    """Search the web for up-to-date information. Handles retries automatically."""
    if tavily is None:
        return "Web search unavailable: TAVILY_API_KEY not set in .env"

    def _search() -> str:
        results: Any = tavily.search(query, max_results=5)
        return "\n".join([str(r["content"]) for r in results["results"]])

    return retry_operation(_search)


@tool  # type: ignore[misc]
def save_to_notes(content: str, topic: str = "general") -> str:
    """Save important information to research notes. Specify a topic for organization."""
    os.makedirs("notes", exist_ok=True)
    safe_chars: str = "".join(
        c for c in topic if c.isalnum() or c in (" ", "-", "_")
    ).strip()
    filename: str = safe_chars.replace(" ", "_") or "general"
    filepath: str = f"notes/{filename}.txt"
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"\n\n--- {datetime.now()} ---\n")
            f.write(content)
        return f"Saved to notes/{filename}.txt"
    except Exception as exc:
        return f"Error saving notes: {exc}"


@tool  # type: ignore[misc]
def calculate(expression: str) -> str:
    """Perform mathematical calculations safely."""
    try:
        result: Any = eval(expression, {"__builtins__": {}})  # noqa: S307
        return str(result)
    except Exception as exc:
        return f"Calculation error: {exc}"


@tool  # type: ignore[misc]
def zapier_execute(action: str, params: str) -> str:
    """Execute a real-world action via Zapier SDK (Google Calendar, Gmail, Slack).

    Use ONLY when the user wants to DO something in the real world.

    Available actions (pass params as a valid JSON string):

    1. "reschedule-meeting"
       Finds a calendar event, moves it, notifies Slack.
       params: '{"search_term":"Standup","new_start":"2026-04-20T10:00:00-00:00",
                 "new_end":"2026-04-20T10:30:00-00:00","slack_channel":"#general"}'

    2. "send-email"
       Sends an email via Gmail.
       params: '{"to":"alice@example.com","subject":"Hello","body":"Hi there"}'

    3. "create-event"
       Creates a new Google Calendar event.
       params: '{"title":"Team Sync","start":"2026-04-21T14:00:00-00:00",
                 "end":"2026-04-21T14:30:00-00:00"}'

    4. "slack-message"
       Sends a message to a Slack channel.
       params: '{"channel":"#engineering","message":"Build complete!"}'

    RULES:
    - All datetimes must be ISO 8601: 2026-04-20T10:00:00-00:00
    - params must be valid JSON with double-quoted keys and string values
    """
    try:
        params_dict: dict[str, Any] = (
            json.loads(params) if isinstance(params, str) else dict(params)
        )
        response = requests.post(
            f"{ZAPIER_SERVICE_URL}/actions/dispatch",
            json={"action": action, "params": params_dict},
            timeout=30,
        )
        if response.status_code == 200:
            data: dict[str, Any] = response.json()
            return f"Action '{action}' succeeded: {data.get('message', 'Done')}"
        try:
            err: str = str(response.json().get("error", response.text))
        except Exception:
            err = response.text
        return f"Action '{action}' failed (HTTP {response.status_code}): {err}"
    except requests.exceptions.ConnectionError:
        return (
            "Zapier service is not running. "
            "Start it: cd zapier-service && node server.js"
        )
    except json.JSONDecodeError as exc:
        return f"Invalid JSON in params: {exc}. Use double-quoted keys and values."
    except Exception as exc:
        return f"Unexpected error in zapier_execute: {exc}"


@tool  # type: ignore[misc]
def list_zapier_connections() -> str:
    """List all apps currently connected to Zapier.

    Call this before zapier_execute if you need to confirm an app is connected
    (e.g., Gmail, Slack, Google Calendar).
    """
    try:
        response = requests.get(f"{ZAPIER_SERVICE_URL}/connections", timeout=10)
        if response.status_code == 200:
            data: dict[str, Any] = response.json()
            connections: List[dict[str, Any]] = data.get("connections", [])
            if not connections:
                return "No apps connected. Visit zapier.com/app/connections to add apps."
            lines: List[str] = ["Connected Zapier apps:"]
            for conn in connections:
                lines.append(
                    f"  - {conn.get('app', 'unknown')} "
                    f"(Label: {conn.get('label', 'N/A')})"
                )
            return "\n".join(lines)
        return f"Could not fetch connections (HTTP {response.status_code})."
    except requests.exceptions.ConnectionError:
        return "Zapier service not running. Start it: cd zapier-service && node server.js"
    except Exception as exc:
        return f"Error checking Zapier connections: {exc}"


TOOLS: List[Any] = [
    search_web,
    save_to_notes,
    calculate,
    zapier_execute,
    list_zapier_connections,
]

ZAPIER_TOOLS: List[Any] = [zapier_execute, list_zapier_connections]