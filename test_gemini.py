import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"Key loaded: {api_key[:10]}...")

genai.configure(api_key=api_key)
print(f"GenAI Version: {genai.__version__}")
print(f"GenAI File: {genai.__file__}")

try:
    print("Listing models...", flush=True)
    count = 0
    for m in genai.list_models():
        print(f"Found: {m.name} - {m.supported_generation_methods}", flush=True)
        count += 1
    
    if count == 0:
        print("WARNING: No models found!", flush=True)

    print("\nTesting generation with gemini-1.5-flash...", flush=True)
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Hello")
        print(f"Response (flash): {response.text}", flush=True)
    except Exception as e:
        print(f"Flash Failed: {e}", flush=True)
        print("\nTesting generation with gemini-pro...", flush=True)
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("Hello")
            print(f"Response (pro): {response.text}", flush=True)
        except Exception as e2:
            print(f"Pro Failed: {e2}", flush=True)
except Exception as e:
    print(f"General Error: {e}", flush=True)
