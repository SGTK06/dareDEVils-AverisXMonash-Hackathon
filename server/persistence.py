"""Small Supabase REST adapter; the API remains usable without credentials."""
import os
from datetime import datetime, timezone
from typing import Any
import httpx

def save_classification(email_id: str, payload: dict[str, Any]) -> None:
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return
    body = {"email_id": email_id, **payload, "updated_at": datetime.now(timezone.utc).isoformat()}
    response = httpx.post(f"{url.rstrip('/')}/rest/v1/mail_classifications", headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}, json=body, timeout=15)
    response.raise_for_status()
