from langchain.tools import tool
from datetime import datetime
import os
import time
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def retry_operation(func, retries=3, delay=1):
    for attempt in range(retries):
        try:
            return func()
        except Exception as e:
            if attempt == retries - 1:
                return f"Error after {retries} retries: {str(e)}"
            time.sleep(delay)

@tool
def search_web(query: str) -> str:
    """Search the web for up-to-date information. Handles retries automatically."""
    def _search():
        results = tavily.search(query, max_results=5)
        return "\n".join([r["content"] for r in results["results"]])
    
    return retry_operation(_search)

@tool
def save_to_notes(content: str, topic: str = "general") -> str:
    """Save important information to research notes. Specify a topic for organization."""
    # Ensure notes directory exists
    os.makedirs("notes", exist_ok=True)
    
    # Sanitize topic
    filename = "".join([c for c in topic if c.isalnum() or c in (' ', '-', '_')]).strip()
    filename = filename.replace(" ", "_")
    filepath = f"notes/{filename}.txt"
    
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"\n\n--- {datetime.now()} ---\n")
            f.write(content)
        return f"Saved to notes/{filename}.txt"
    except Exception as e:
        return f"Error saving notes: {e}"

@tool
def calculate(expression: str) -> str:
    """Perform mathematical calculations."""
    try:
        return str(eval(expression, {"__builtins__": {}}))
    except Exception as e:
        return f"Error: {e}"

TOOLS = [search_web, save_to_notes, calculate]

