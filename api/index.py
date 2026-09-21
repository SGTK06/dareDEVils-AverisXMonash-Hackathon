"""Vercel entry point for the FastAPI backend.

Vercel invokes this module as an ASGI-compatible Python Function. The wrapper
removes the public /api prefix before handing requests to the existing app.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATA_DIR", str(ROOT / "data_v2"))
os.environ.setdefault("GROUND_TRUTH", str(ROOT / "data_v2" / "ground_truth.json"))

from app import app as _app  # noqa: E402


async def app(scope, receive, send):
    if scope["type"] == "http" and scope.get("path", "").startswith("/api"):
        scope = dict(scope)
        scope["path"] = scope["path"][4:] or "/"
        scope["raw_path"] = scope.get("raw_path", b"")[4:] or b"/"
    await _app(scope, receive, send)

