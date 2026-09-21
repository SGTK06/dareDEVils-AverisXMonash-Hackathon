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
    CORS_ORIGINS   comma-separated allowed browser origins (default: *)
"""
import json
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from classification import MailClassifier
from comparison_service import compare_email
from persistence import save_classification, save_classifications_batch, get_classifications_batch, save_comparison, get_comparisons_batch, save_pipeline_run, get_recent_runs

import scoring

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
INBOX_DIR = DATA_DIR / "inbox"
ATTACH_DIR = DATA_DIR / "attachments"
GROUND_TRUTH_PATH = Path(os.environ.get("GROUND_TRUTH", "/secrets/ground_truth.json"))
SAMPLE_PATH = DATA_DIR / "sample_submission.json"
REVEAL_GT = os.environ.get("REVEAL_GT", "0") == "1"
JUDGE_TOKEN = os.environ.get("JUDGE_TOKEN")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

app = FastAPI(title="SDOC Hackathon Inbox", version="2.0",
              description="Serves the shipping-docs inbox and scores submissions. "
              "Ground truth is held privately and never served.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"]
)
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
    inbox_emails = _load_inbox()
    email_ids = [e["email_id"] for e in inbox_emails]
    cached = get_classifications_batch(email_ids)
    
    results = []
    uncached_emails = [e for e in inbox_emails if e["email_id"] not in cached]
    classified = classifier.classify_many(uncached_emails)
    classified_dict = {e["email_id"]: c for e, c in zip(uncached_emails, classified)}
    
    payloads = []
    for email in inbox_emails:
        eid = email["email_id"]
        if eid in cached:
            results.append(cached[eid])
        else:
            result = classified_dict[eid].to_dict()
            payload = {"email_id": eid, **result, "status": "NEEDS_REVIEW" if result["check_required"] else "CLASSIFIED"}
            payloads.append(payload)
            results.append(payload)
            
    if payloads:
        save_classifications_batch(payloads)
    return {"count": len(results), "results": results}

@app.post("/tests/classification")
def run_classification_test():
    truth = _load_ground_truth()
    results = []
    matrix = {actual: {predicted: 0 for predicted in TEST_CATEGORIES} for actual in TEST_CATEGORIES}
    emails = _load_inbox()
    classified = classifier.classify_many(emails)
    for email, classification in zip(emails, classified):
        result = classification.to_dict()
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
    result_payload = {"total": total, "correct": sum(item["correct"] for item in results), "accuracy": sum(item["correct"] for item in results) / total if total else 0, "review_count": sum(item["check_required"] for item in results), "confusion_matrix": matrix, "per_category": per_category, "macro": macro, "results": results}
    # Persist test run to database
    try:
        run_id = save_pipeline_run(
            run_type="classification_test",
            config={"categories": TEST_CATEGORIES},
            results=result_payload,
            score=result_payload["accuracy"],
            email_count=total,
        )
        result_payload["run_id"] = run_id
    except Exception as e:
        print("save_pipeline_run classification_test error:", repr(e))
    return result_payload


@app.post("/tests/comparison")
def run_comparison_test():
    """Evaluate the comparison pipeline against the v2 ground truth."""
    truth = _load_ground_truth()
    comparison_ids = [eid for eid, item in truth.items() if item.get("category") == "BL_COMPARISON"]
    results = []
    status_labels = ["OK", "MISMATCH", "NEEDS_REVIEW"]
    matrix = {actual: {predicted: 0 for predicted in status_labels} for actual in status_labels}
    field_labels = ["shipper", "consignee", "notify_party", "port_of_loading", "port_of_discharge", "container_count", "gross_weight_kg"]
    field_stats = {field: {"tp": 0, "fp": 0, "fn": 0, "exact": 0, "total": 0} for field in field_labels}
    review_reasons = {reason: {"total": 0, "caught": 0} for reason in ["wrong_doc_type", "missing_attachment", "unreadable", "missing_value"]}
    for email_id in comparison_ids:
        gold = truth[email_id]
        prediction = compare_email(email_id, DATA_DIR)
        actual_status = gold.get("status", "OK")
        predicted_status = prediction.get("status", "NEEDS_REVIEW")
        has_pair = len(get_email(email_id).get("attachments") or []) >= 2
        if has_pair:
            matrix[actual_status][predicted_status] += 1
        gold_fields = set(gold.get("defect_fields", []))
        predicted_fields = set(prediction.get("defect_fields", []))
        comparable = has_pair and actual_status in {"OK", "MISMATCH"}
        if comparable:
            for field in field_labels:
                gold_bad, predicted_bad = field in gold_fields, field in predicted_fields
                field_stats[field]["total"] += 1
                field_stats[field]["exact"] += int(gold_bad == predicted_bad)
                field_stats[field]["tp"] += int(gold_bad and predicted_bad)
                field_stats[field]["fp"] += int(not gold_bad and predicted_bad)
                field_stats[field]["fn"] += int(gold_bad and not predicted_bad)
        reason = gold.get("review_reason")
        if actual_status == "NEEDS_REVIEW" and reason in review_reasons:
            review_reasons[reason]["total"] += 1
            review_reasons[reason]["caught"] += int(predicted_status == "NEEDS_REVIEW")
        results.append({
            "email_id": email_id,
            "subject": get_email(email_id).get("subject", ""),
            "actual": actual_status,
            "predicted": predicted_status,
            "actual_fields": sorted(gold_fields),
            "predicted_fields": sorted(predicted_fields),
            "review_reason": prediction.get("review_reason"),
            "has_attachment_pair": has_pair,
            "correct": actual_status == predicted_status and gold_fields == predicted_fields,
        })

    def prf(stats):
        precision = stats["tp"] / (stats["tp"] + stats["fp"]) if stats["tp"] + stats["fp"] else 0
        recall = stats["tp"] / (stats["tp"] + stats["fn"]) if stats["tp"] + stats["fn"] else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        return {"precision": precision, "recall": recall, "f1": f1, "support": stats["tp"] + stats["fn"], "exact_accuracy": stats["exact"] / stats["total"] if stats["total"] else 0}

    comparable_count = 0
    pair_count = 0
    pair_exact = 0
    for eid, item in truth.items():
        if item.get("category") != "BL_COMPARISON":
            continue
        email = get_email(eid)
        has_pair = len(email.get("attachments") or []) >= 2
        if has_pair:
            pair_count += 1
        if has_pair and item.get("status") != "NEEDS_REVIEW":
            comparable_count += 1
            if has_pair:
                prediction = next((row for row in results if row["email_id"] == eid), None)
                if prediction and set(prediction["actual_fields"]) == set(prediction["predicted_fields"]):
                    pair_exact += 1
    review_total = sum(item["total"] for item in review_reasons.values())
    review_caught = sum(item["caught"] for item in review_reasons.values())
    predicted_review = sum(item["predicted"] == "NEEDS_REVIEW" for item in results)
    review_precision = review_caught / predicted_review if predicted_review else 0
    review_recall = review_caught / review_total if review_total else 0
    result_payload = {
        "total": len(results), "comparable_total": comparable_count, "pair_total": pair_count,
        "not_comparable_total": len(results) - pair_count, "review_total": review_total,
        "status_confusion_matrix": matrix,
        "field_metrics": {field: prf(stats) for field, stats in field_stats.items()},
        "macro_field": {key: sum(metrics[key] for metrics in {field: prf(stats) for field, stats in field_stats.items()}.values()) / len(field_labels) for key in ("precision", "recall", "f1", "exact_accuracy")},
        "exact_defect_field_accuracy": sum(
            set(item["actual_fields"]) == set(item["predicted_fields"])
            for item in results
            if item.get("has_attachment_pair") and truth[item["email_id"]].get("status") != "NEEDS_REVIEW"
        ) / comparable_count if comparable_count else 0,
        "pair_exact_defect_field_accuracy": pair_exact / pair_count if pair_count else 0,
        "review_precision": review_precision, "review_recall": review_recall,
        "review_f1": 2 * review_precision * review_recall / (review_precision + review_recall) if review_precision + review_recall else 0,
        "review_reasons": review_reasons, "results": results,
    }
    try:
        run_id = save_pipeline_run(
            run_type="full_pipeline",
            config={},
            results=result_payload,
            score=result_payload.get("pair_exact_defect_field_accuracy"),
            email_count=len(results),
        )
        result_payload["run_id"] = run_id
    except Exception as e:
        print("save_pipeline_run full_pipeline error:", repr(e))
    return result_payload

@app.patch("/classifications/{email_id}")
def correct_classification(email_id: str, correction: Correction):
    get_email(email_id)
    payload = {"status": "RESOLVED", "check_required": False, "review_reason": None, "corrected_values": correction.corrected_values}
    if correction.category:
        payload["category"] = correction.category
    save_classification(email_id, payload)
    return {"email_id": email_id, **payload}


# --------------------------------------------------------------------------
# comparison persistence
# --------------------------------------------------------------------------
@app.get("/comparisons/batch")
def get_comparisons_batch_endpoint(ids: str):
    """Fetch cached comparisons for a batch of emails."""
    email_ids = [eid.strip() for eid in ids.split(",") if eid.strip()]
    cached = get_comparisons_batch(email_ids)
    
    # Clean up fields JSON serialization for the frontend
    for row in cached.values():
        if isinstance(row.get("fields"), str):
            try:
                row["fields"] = json.loads(row["fields"])
            except Exception:
                row["fields"] = []
                
    return cached


@app.get("/comparisons/{email_id}")
def run_comparison(email_id: str):
    get_email(email_id)
    cached = get_comparisons_batch([email_id])
    if email_id in cached:
        row = cached[email_id]
        fields = row.get("fields", [])
        if isinstance(fields, str):
            try:
                fields = json.loads(fields)
            except Exception:
                fields = []
        return {
            "status": row.get("status", "NEEDS_REVIEW"),
            "review_reason": row.get("reason"),
            "fields": fields
        }
    return compare_email(email_id, DATA_DIR)


@app.post("/comparisons/{email_id}")
def persist_comparison(email_id: str, request_body: dict):
    """Save a comparison result for an email."""
    get_email(email_id)  # validate email exists
    save_comparison(
        email_id=email_id,
        fields=request_body.get("fields", []),
        status=request_body.get("status", "CLASSIFIED"),
        result_text=request_body.get("result_text"),
        reason=request_body.get("reason"),
    )
    return {"email_id": email_id, "persisted": True}


@app.get("/comparisons/batch")
def batch_comparisons(ids: str = ""):
    """Fetch cached comparison results. Pass comma-separated email IDs."""
    if not ids:
        return {}
    email_ids = [eid.strip() for eid in ids.split(",") if eid.strip()]
    return get_comparisons_batch(email_ids)


# --------------------------------------------------------------------------
# pipeline run history
# --------------------------------------------------------------------------
@app.get("/runs")
def list_runs(run_type: str | None = None, limit: int = 20):
    """Return recent pipeline runs from Supabase."""
    return get_recent_runs(run_type=run_type, limit=limit)


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
    try:
        run_id = save_pipeline_run(
            run_type="submission",
            config={},
            results=result,
            score=result.get("final_score"),
            email_count=len(sub),
        )
        result["run_id"] = run_id
    except Exception as e:
        print("save_pipeline_run submission error:", repr(e))
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
