"""Application comparison pipeline for SI/BL document pairs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from comparison.legacy_compare import find_attachment_pair_for_email
from comparison.processing_steps.documents import document_text as load_document_text
from comparison.processing import FIELD_ORDER, extract_fields
from comparison.pipeline import compare_documents
from llm.gemini import verify_discrepancy
from persistence import get_field_overrides


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
        return {
            "email_id": email_id,
            "status": "NEEDS_REVIEW",
            "review_reason": "missing_attachment",
            "has_defect": False,
            "defect_fields": [],
            "fields": [],
        }

    try:
        si_path, bl_path = find_attachment_pair_for_email(email_id, root)
        si_text, bl_text = document_text(si_path), document_text(bl_path)
        raw_si, raw_bl = extract_fields(si_text), extract_fields(bl_text)
        
        # 1. Apply HITL Overrides
        overrides = get_field_overrides(email_id)
        
        if "si" in overrides:
            raw_si.update(overrides["si"])
        if "bl" in overrides:
            raw_bl.update(overrides["bl"])
            
        raw_results = compare_documents(raw_si, raw_bl)
    except FileNotFoundError:
        return {"email_id": email_id, "status": "NEEDS_REVIEW", "review_reason": "missing_attachment", "has_defect": False, "defect_fields": [], "fields": []}
    except Exception as exc:
        return {"email_id": email_id, "status": "NEEDS_REVIEW", "review_reason": "unreadable", "has_defect": False, "defect_fields": [], "fields": [], "error": str(exc)}

    fields = [_field_payload(field, raw_results[field], raw_si, raw_bl) for field in FIELD_ORDER]
    
    # 2. Gemini Verification for Mismatches
    for f in fields:
        if f["result"] == "mismatch":
            try:
                verification = verify_discrepancy(f["field"], str(f["si"]), str(f["bl"]))
                if not verification.get("is_mismatch", True):
                    f["result"] = "match"
                    f["evidence"] = f"{f['evidence']} | [Gemini Verified] {verification.get('explanation', '')}"
                else:
                    f["evidence"] = f"{f['evidence']} | [Gemini Confirmed] {verification.get('explanation', '')}"
            except Exception as e:
                f["evidence"] = f"{f['evidence']} | [Gemini Failed: {e}]"
                
    review = [field for field in fields if field["result"] == "review"]
    mismatches = [field["field"] for field in fields if field["result"] == "mismatch"]
    
    # 3. Clean Discrepancy & Attention Report
    report_lines = []
    needs_attention = []
    
    for f in fields:
        if f["result"] == "mismatch":
            report_lines.append(f"- {f['field']}:\n  SI: {f['si']}\n  BL: {f['bl']}")
        elif f["result"] == "review":
            needs_attention.append(f"- {f['field']} (Needs Review: {f['evidence']})")
            
    if not mismatches and not review:
        report = "No mismatch detected."
    else:
        report = "Discrepancies found:\n" + "\n".join(report_lines) if mismatches else ""
        if needs_attention:
            report += ("\n\n" if report else "") + "Needs Attention:\n" + "\n".join(needs_attention)
            report += "\nAction: Please review and provide overrides for ambiguous fields."
            
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
        "result_text": report.strip()
    }
