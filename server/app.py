#!/usr/bin/env python3
"""
SDOC hackathon inbox + scoring server.

Serves the dataset to participants over HTTP and scores their submissions
against a ground-truth file that is mounted PRIVATELY and never exposed on any
endpoint.

Public (participant) endpoints
    GET  /health                      liveness probe
    GET  /                            API index
    GET  /emails                      list all email records (no labels)
    GET  /emails/{email_id}           one email record
    GET  /attachments/{path}          download an SI/BL attachment
    GET  /sample_submission           the exact output shape to produce
    POST /submit                      score a submission -> scoreboard JSON

Judge-only endpoint (guarded by X-Judge-Token, off unless JUDGE_TOKEN is set)
    GET  /ground_truth                the labels (returns 404 when disabled)

Environment
    DATA_DIR       default /data           (mount data_v2 here, read-only)
    GROUND_TRUTH   default /secrets/ground_truth.json   (private mount)
    REVEAL_GT      "1" to enable /ground_truth (default off)
    JUDGE_TOKEN    if set, /ground_truth requires header X-Judge-Token: <token>
"""
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from classification import MailClassifier
from persistence import save_classification

import scoring

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
INBOX_DIR = DATA_DIR / "inbox"
ATTACH_DIR = DATA_DIR / "attachments"
GROUND_TRUTH_PATH = Path(os.environ.get("GROUND_TRUTH", "/secrets/ground_truth.json"))
SAMPLE_PATH = DATA_DIR / "sample_submission.json"
REVEAL_GT = os.environ.get("REVEAL_GT", "0") == "1"
JUDGE_TOKEN = os.environ.get("JUDGE_TOKEN")

app = FastAPI(title="SDOC Hackathon Inbox", version="2.0",
              description="Serves the shipping-docs inbox and scores submissions. "
              "Ground truth is held privately and never served.")
classifier = MailClassifier()
TEST_CATEGORIES = ["BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"]

class Correction(BaseModel):
    corrected_values: dict = Field(default_factory=dict)
    category: str | None = None

@app.get("/classifications/{email_id}")
def classify_email(email_id: str):
    email = get_email(email_id)
    result = classifier.classify_with_fallback(email).to_dict()
    save_classification(email_id, {**result, "status": "NEEDS_REVIEW" if result["check_required"] else "CLASSIFIED"})
    return {"email_id": email_id, **result}

@app.post("/classifications/run")
def classify_inbox():
    results = []
    for email in _load_inbox():
        result = classifier.classify_with_fallback(email).to_dict()
        save_classification(email["email_id"], {**result, "status": "NEEDS_REVIEW" if result["check_required"] else "CLASSIFIED"})
        results.append({"email_id": email["email_id"], **result})
    return {"count": len(results), "results": results}

@app.post("/tests/classification")
def run_classification_test():
    truth = _load_ground_truth()
    results = []
    matrix = {actual: {predicted: 0 for predicted in TEST_CATEGORIES} for actual in TEST_CATEGORIES}
    for email in _load_inbox():
        result = classifier.classify_with_fallback(email).to_dict()
        actual = truth.get(email["email_id"], {}).get("category", "GENERAL")
        predicted = result["category"] if result["category"] in TEST_CATEGORIES else "GENERAL"
        matrix.setdefault(actual, {label: 0 for label in TEST_CATEGORIES})
        matrix[actual].setdefault(predicted, 0)
        matrix[actual][predicted] += 1
        results.append({"email_id": email["email_id"], "subject": email.get("subject", ""), "actual": actual, "predicted": predicted, "confidence": result["confidence"], "provider": result["provider"], "check_required": result["check_required"], "review_reason": result.get("review_reason"), "correct": actual == predicted})
    total = len(results)
    per_category = {}
    for label in TEST_CATEGORIES:
        tp = matrix[label][label]
        fp = sum(matrix[actual][label] for actual in TEST_CATEGORIES if actual != label)
        fn = sum(matrix[label][predicted] for predicted in TEST_CATEGORIES if predicted != label)
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        per_category[label] = {"support": sum(matrix[label].values()), "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0}
    macro = {key: sum(item[key] for item in per_category.values()) / len(TEST_CATEGORIES) for key in ("precision", "recall", "f1")}
    return {"total": total, "correct": sum(item["correct"] for item in results), "accuracy": sum(item["correct"] for item in results) / total if total else 0, "review_count": sum(item["check_required"] for item in results), "confusion_matrix": matrix, "per_category": per_category, "macro": macro, "results": results}

@app.patch("/classifications/{email_id}")
def correct_classification(email_id: str, correction: Correction):
    get_email(email_id)
    payload = {"status": "RESOLVED", "check_required": False, "review_reason": None, "corrected_values": correction.corrected_values}
    if correction.category:
        payload["category"] = correction.category
    save_classification(email_id, payload)
    return {"email_id": email_id, **payload}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _load_inbox():
    """All email records, sorted by id. Labels are NOT here — inbox files only
    contain email_id/from/subject/body/attachments."""
    out = []
    for p in sorted(INBOX_DIR.glob("email_*.json")):
        out.append(json.loads(p.read_text()))
    return out


def _load_ground_truth():
    if not GROUND_TRUTH_PATH.exists():
        raise HTTPException(503, "ground truth not mounted; scoring unavailable")
    return json.loads(GROUND_TRUTH_PATH.read_text())


# --------------------------------------------------------------------------
# public endpoints
# --------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok",
            "emails": len(list(INBOX_DIR.glob("email_*.json"))),
            "scoring_available": GROUND_TRUTH_PATH.exists()}


@app.get("/")
def index():
    return {
        "service": "SDOC Hackathon Inbox",
        "endpoints": {
            "GET /emails": "list all email records",
            "GET /emails/{email_id}": "one email record",
            "GET /attachments/{path}": "download an SI/BL attachment",
            "GET /sample_submission": "the output shape you must produce",
            "POST /submit": "score your submission (JSON body: {email_id: {...}})",
        },
        "note": "Ground truth is private. Score yourself via POST /submit.",
    }


@app.get("/emails")
def list_emails():
    return _load_inbox()


@app.get("/emails/{email_id}")
def get_email(email_id: str):
    p = INBOX_DIR / f"{email_id}.json"
    if not p.exists():
        raise HTTPException(404, f"no such email: {email_id}")
    return json.loads(p.read_text())


@app.get("/attachments/{path:path}")
def get_attachment(path: str):
    # normalise and confine to ATTACH_DIR (no path traversal)
    target = (ATTACH_DIR / path).resolve()
    if not str(target).startswith(str(ATTACH_DIR.resolve())) or not target.is_file():
        raise HTTPException(404, f"no such attachment: {path}")
    return FileResponse(target)


@app.get("/sample_submission")
def sample_submission():
    if not SAMPLE_PATH.exists():
        raise HTTPException(404, "sample_submission.json not found")
    return json.loads(SAMPLE_PATH.read_text())


@app.post("/submit")
async def submit(request: Request):
    """Score a submission against the private ground truth. The ground truth is
    never returned — only the scoreboard."""
    try:
        sub = await request.json()
    except Exception:
        raise HTTPException(400, "body must be JSON: {email_id: {category,status,has_defect,defect_fields}}")
    if not isinstance(sub, dict):
        raise HTTPException(400, "submission must be a JSON object keyed by email_id")
    truth = _load_ground_truth()
    result = scoring.score_all(truth, sub)
    return JSONResponse(result)


# --------------------------------------------------------------------------
# judge-only (disabled by default)
# --------------------------------------------------------------------------
@app.get("/ground_truth")
def ground_truth(x_judge_token: Optional[str] = Header(default=None)):
    if not REVEAL_GT:
        raise HTTPException(404, "not found")
    if JUDGE_TOKEN and x_judge_token != JUDGE_TOKEN:
        raise HTTPException(403, "bad judge token")
    return _load_ground_truth()
