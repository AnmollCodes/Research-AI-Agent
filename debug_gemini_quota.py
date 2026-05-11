import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import time

load_dotenv()

def test_gemini():
    print("Testing Gemini API access...")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found in environment.")
        return

    print(f"API Key present: {api_key[:10]}...")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        temperature=0,
        max_retries=0
    )
    
    try:
        print("Sending test message...")
        start = time.time()
        response = llm.invoke([HumanMessage(content="Hello, are you working?")])
        print(f"Success! Response: {response.content}")
        print(f"Time taken: {time.time() - start:.2f}s")
    except Exception as e:
        print(f"FAILED. Error details:\n{e}")

if __name__ == "__main__":
    test_gemini()
