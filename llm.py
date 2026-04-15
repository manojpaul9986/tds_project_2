import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("AIPROXY_TOKEN")

URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

def call_llm(payload):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.post(URL, json=payload, headers=headers)
    return response.json()

def get_metadata(df):
    sample = df.head(10).to_json()

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": sample}]
    }

    return call_llm(payload)

def check_binnability(stats):
    # simplified for modular design
    return stats