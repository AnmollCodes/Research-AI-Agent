import requests
import json

url = "http://localhost:8000/chat"
payload = {"message": "hello", "thread_id": "debug_1"}
headers = {"Content-Type": "application/json"}

print(f"Sending request to {url}...")
try:
    with requests.post(url, json=payload, stream=True) as r:
        print(f"Status: {r.status_code}")
        for line in r.iter_lines():
            if line:
                print(line.decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
