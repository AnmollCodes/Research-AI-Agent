
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import time

load_dotenv()

def test_model(model_name):
    print(f"\n--- Testing {model_name} ---")
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        max_retries=0
    )
    try:
        start = time.time()
        res = llm.invoke([HumanMessage(content="Hello")])
        print(f"✅ SUCCESS: {model_name}")
        print(f"Response: {res.content}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {model_name}")
        print(f"Error: {str(e)[:200]}...") # truncate error
        return False

models_to_test = [
    "gemini-1.5-flash",
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash", 
    "gemini-exp-1206",
    "gemini-1.5-pro"
]

available = []
for m in models_to_test:
    if test_model(m):
        available.append(m)

print(f"\n\nSummary: Working models: {available}")
