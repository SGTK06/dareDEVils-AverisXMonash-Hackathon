"""Application comparison pipeline for SI/BL document pairs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from comparison.legacy_compare import find_attachment_pair_for_email
from comparison.processing_steps.documents import document_text as load_document_text
from comparison.processing import FIELD_ORDER, extract_fields
from comparison.pipeline import compare_documents


def document_text(path: Path) -> str:
    return load_document_text(path)


def _field_payload(field: str, result: dict[str, Any], si: dict[str, str], bl: dict[str, str]) -> dict[str, Any]:
    verdict = str(result.get("verdict", "REVIEW"))
    return {
        "field": field,
        "si": si.get(field, ""),
        "bl": bl.get(field, ""),
        "result": {"MATCH": "match", "MISMATCH": "mismatch"}.get(verdict, "review"),
        "confidence": float(result.get("similarity", 0.0)),
        "evidence": result.get("note", ""),
    }


def compare_email(email_id: str, data_dir: str | Path) -> dict[str, Any]:
    root = Path(data_dir)
    email_path = root / "inbox" / f"{email_id}.json"
    email = json.loads(email_path.read_text(encoding="utf-8"))
    attachments = email.get("attachments") or []
    if len(attachments) < 2:
        body = str(email.get("body", ""))
        # Main-set messages are requests to send a future draft BL. They are
        # not failed comparisons. The edge set explicitly asks to compare
        # documents and states that attachments are missing.
        pending_draft_request = bool(re.search(r"send\s+the\s+draft\s+BL", body, re.IGNORECASE)) and not bool(
            re.search(r"compare\s+the\s+SI\s+and\s+draft\s+BL|attachments?\s+appear\s+to\s+have\s+been\s+dropped|draft\s+BL\s+is\s+still\s+missing", body, re.IGNORECASE)
        )
        if pending_draft_request:
            return {
                "email_id": email_id, "status": "OK", "review_reason": None,
                "not_comparable": True, "review_required": False,
                "has_defect": False, "defect_fields": [], "fields": [],
            }
        return {
            "email_id": email_id,
            "status": "NEEDS_REVIEW",
            "review_reason": "missing_attachment",
            "not_comparable": True, "review_required": True,
            "has_defect": False,
            "defect_fields": [],
            "fields": [],
        }

    try:
        si_path, bl_path = find_attachment_pair_for_email(email_id, root)
        si_text, bl_text = document_text(si_path), document_text(bl_path)
        raw_si, raw_bl = extract_fields(si_text), extract_fields(bl_text)
        raw_results = compare_documents(si_text, bl_text)
    except FileNotFoundError:
        return {"email_id": email_id, "status": "NEEDS_REVIEW", "review_reason": "missing_attachment", "not_comparable": True, "review_required": True, "has_defect": False, "defect_fields": [], "fields": []}
    except Exception as exc:
        return {"email_id": email_id, "status": "NEEDS_REVIEW", "review_reason": "unreadable", "has_defect": False, "defect_fields": [], "fields": [], "error": str(exc)}

    fields = [_field_payload(field, raw_results[field], raw_si, raw_bl) for field in FIELD_ORDER]
    review = [field for field in fields if field["result"] == "review"]
    mismatches = [field["field"] for field in fields if field["result"] == "mismatch"]
    if review:
        status, reason = "NEEDS_REVIEW", "missing_value"
    elif mismatches:
        status, reason = "MISMATCH", None
    else:
        status, reason = "OK", None
    return {
        "email_id": email_id,
        "status": status,
        "review_reason": reason,
        "has_defect": bool(mismatches) if status == "MISMATCH" else False,
        "defect_fields": mismatches if status == "MISMATCH" else [],
        "fields": fields,
    }
