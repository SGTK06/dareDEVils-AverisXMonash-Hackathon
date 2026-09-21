import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
import httpx
from datetime import datetime, timezone

url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
print(f"URL: {url}")
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}
body = {
    "run_type": "classification_test",
    "status": "success",
    "config": {},
    "results": {"test": "test"},
    "score": 0.8,
    "email_count": 520,
    "finished_at": datetime.now(timezone.utc).isoformat()
}

response = httpx.post(f"{url}/rest/v1/pipeline_runs", headers=headers, json=body)
print(response.status_code)
print(response.text)
