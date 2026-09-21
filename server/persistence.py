"""Supabase REST adapter for persistent state. Falls back gracefully when credentials are missing."""
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import httpx

_TIMEOUT = 15


def _headers() -> dict[str, str] | None:
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }


def _base_url() -> str:
    return os.getenv("SUPABASE_URL", "").rstrip("/")


# ── Classifications (existing) ──────────────────────────────


def save_classification(email_id: str, payload: dict[str, Any]) -> None:
    headers = _headers()
    if not headers:
        return
    body = {"email_id": email_id, **payload, "updated_at": datetime.now(timezone.utc).isoformat()}
    response = httpx.post(
        f"{_base_url()}/rest/v1/mail_classifications",
        headers=headers,
        json=body,
        timeout=_TIMEOUT,
    )
    response.raise_for_status()


def save_classifications_batch(payloads: list[dict[str, Any]]) -> None:
    headers = _headers()
    if not headers or not payloads:
        return
    
    timestamp = datetime.now(timezone.utc).isoformat()
    body = []
    for p in payloads:
        body.append({
            "email_id": p.get("email_id"),
            "category": p.get("category"),
            "confidence": p.get("confidence"),
            "scores": p.get("scores", {}),
            "check_required": p.get("check_required", False),
            "review_reason": p.get("review_reason"),
            "status": p.get("status", "CLASSIFIED"),
            "updated_at": timestamp,
        })
    
    response = httpx.post(
        f"{_base_url()}/rest/v1/mail_classifications",
        headers={**headers, "Prefer": "resolution=merge-duplicates"},
        json=body,
        timeout=_TIMEOUT,
    )
    response.raise_for_status()


def get_classifications_batch(email_ids: list[str]) -> dict[str, dict]:
    """Fetch cached classifications for a batch of email IDs."""
    headers = _headers()
    if not headers or not email_ids:
        return {}
    
    # Split into chunks of 100 to avoid overly long URLs
    results = {}
    headers_get = {k: v for k, v in headers.items() if k != "Prefer"}
    
    for i in range(0, len(email_ids), 100):
        chunk = email_ids[i:i+100]
        ids_param = ",".join(chunk)
        try:
            response = httpx.get(
                f"{_base_url()}/rest/v1/mail_classifications?email_id=in.({ids_param})&select=*",
                headers=headers_get,
                timeout=_TIMEOUT,
            )
            if response.status_code == 200:
                for row in response.json():
                    results[row["email_id"]] = row
        except Exception:
            pass
            
    return results

# ── Comparison Results ───────────────────────────────────────


def save_comparison(
    email_id: str,
    fields: list[dict],
    status: str,
    result_text: str | None = None,
    reason: str | None = None,
) -> None:
    headers = _headers()
    if not headers:
        return
    body = {
        "email_id": email_id,
        "fields": json.dumps(fields) if isinstance(fields, list) else fields,
        "status": status,
        "result_text": result_text,
        "reason": reason,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    response = httpx.post(
        f"{_base_url()}/rest/v1/comparison_results",
        headers=headers,
        json=body,
        timeout=_TIMEOUT,
    )
    response.raise_for_status()


def get_comparisons_batch(email_ids: list[str]) -> dict[str, dict]:
    """Fetch cached comparison results for a batch of email IDs."""
    headers = _headers()
    if not headers or not email_ids:
        return {}
    # Use PostgREST "in" filter
    ids_param = ",".join(email_ids)
    headers_get = {k: v for k, v in headers.items() if k != "Prefer"}
    response = httpx.get(
        f"{_base_url()}/rest/v1/comparison_results?email_id=in.({ids_param})&select=*",
        headers=headers_get,
        timeout=_TIMEOUT,
    )
    if response.status_code != 200:
        return {}
    rows = response.json()
    return {row["email_id"]: row for row in rows}


# ── Pipeline Runs ────────────────────────────────────────────


def save_pipeline_run(
    run_type: str,
    config: dict | None = None,
    results: dict | None = None,
    score: float | None = None,
    email_count: int | None = None,
    status: str = "success",
) -> str | None:
    """Persist a pipeline run and return the generated UUID, or None if DB is unavailable."""
    headers = _headers()
    if not headers:
        return None
    # Ask PostgREST to return the created row
    headers = {**headers, "Prefer": "return=representation"}
    body: dict[str, Any] = {
        "run_type": run_type,
        "status": status,
        "config": config or {},
        "results": results,
        "score": score,
        "email_count": email_count,
        "finished_at": datetime.now(timezone.utc).isoformat() if status != "running" else None,
    }
    response = httpx.post(
        f"{_base_url()}/rest/v1/pipeline_runs",
        headers=headers,
        json=body,
        timeout=_TIMEOUT,
    )
    if response.status_code in (200, 201):
        rows = response.json()
        if rows and isinstance(rows, list):
            return rows[0].get("id")
    print(f"save_pipeline_run failed: {response.status_code} {response.text}")
    return None


def get_recent_runs(run_type: str | None = None, limit: int = 20) -> list[dict]:
    """Fetch recent pipeline runs, optionally filtered by run_type."""
    headers = _headers()
    if not headers:
        return []
    headers_get = {k: v for k, v in headers.items() if k != "Prefer"}
    query = f"{_base_url()}/rest/v1/pipeline_runs?select=*&order=started_at.desc&limit={limit}"
    if run_type:
        query += f"&run_type=eq.{run_type}"
    response = httpx.get(query, headers=headers_get, timeout=_TIMEOUT)
    if response.status_code != 200:
        return []
    return response.json()


# ── Field Overrides (Local JSON Storage) ─────────────────────

def _overrides_path() -> Path:
    from app import DATA_DIR
    return DATA_DIR / "overrides.json"

def get_field_overrides(email_id: str) -> dict[str, dict[str, str]]:
    """Fetch field overrides for an email ID. Returns dict like {'si': {'field': 'val'}, 'bl': {...}}"""
    path = _overrides_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get(email_id, {})
    except Exception:
        return {}

def save_field_override(email_id: str, doc_type: str, field_name: str, value: str) -> None:
    """Save an operator override for an extracted field."""
    path = _overrides_path()
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    if email_id not in data:
        data[email_id] = {}
    if doc_type not in data[email_id]:
        data[email_id][doc_type] = {}
    data[email_id][doc_type][field_name] = value
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
