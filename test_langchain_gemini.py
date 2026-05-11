from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()

models_to_test = ["gemini-pro", "models/gemini-pro", "gemini-1.5-flash", "models/gemini-1.5-flash", "gemini-2.0-flash-exp"]

for m in models_to_test:
    print(f"Testing {m}...")
    try:
        llm = ChatGoogleGenerativeAI(model=m, temperature=0)
        res = llm.invoke([HumanMessage(content="Hi")])
        print(f"SUCCESS: {m}\nResponse: {res.content}")
        break  # Found one!
    except Exception as e:
        print(f"FAILED: {m} - {str(e)[:100]}")
