"""Compare shipping proper-noun fields with regex + Levenshtein distance.

This module intentionally avoids NLP libraries, embeddings, and third-party
packages. It only uses the Python stdlib and a custom dynamic-programming
Levenshtein implementation.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import item_compare

FIELD_ORDER = [
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
    "description_of_goods",
]

REVIEW_THRESHOLD = 0.85

LEGAL_WORDS = {
    "SDN",
    "BHD",
    "LTD",
    "LIMITED",
    "CO",
    "INC",
    "LLC",
    "PTE",
    "GMBH",
    "UAB",
    "Sdn",
    "Bhd",
    "Ltd",
    "Limited",
    "Co",
    "Inc",
    "Llc",
    "Pte",
    "Gmbh",
    "Uab",
}

LABEL_ALIASES = {
    "shipper": {
        "SHIPPER",
        "SHIPPER EXPORTER",
        "SHIPPER / EXPORTER",
        "SHIPPER EXPORTER PRINCIPAL SELLER",
        "EXPORTER",
    },
    "consignee": {
        "CONSIGNEE",
        "CONSIGNEE NON NEGOTIABLE",
        "TO THE ORDER OF",
        "TO THE ORDER OF SHIPPER",
    },
    "notify_party": {
        "NOTIFY PARTY",
        "NOTIFY",
        "NOTIFY PARTY INTERMEDIATE CONSIGNEE",
        "INTERMEDIATE CONSIGNEE",
    },
    "port_of_loading": {
        "PORT OF LOADING",
        "LOAD PORT",
        "POL",
        "PORT OF LOADING POL",
    },
    "port_of_discharge": {
        "PORT OF DISCHARGE",
        "DISCHARGE PORT",
        "POD",
        "PORT OF DISCHARGE POD",
    },
    "container_count": {
        "CONTAINER COUNT",
        "NO OF CONTAINERS OR PACKAGES",
        "NO. OF CONTAINERS OR PACKAGES",
        "NUMBER OF CONTAINERS",
        "NO OF CONTAINERS",
    },
    "gross_weight_kg": {
        "GROSS WEIGHT KG",
        "GROSS WEIGHT (KG)",
        "GROSS WEIGHT (KGS)",
        "GROSS WT KG",
        "GROSS WT (KGS)",
        "GROSS WT (KG)",
    },
    "description_of_goods": {
        "DESCRIPTION OF GOODS",
        "DESCRIPTION",
        "GOODS DESCRIPTION",
        "PARTICULARS FURNISHED BY SHIPPER",
    },
}

CANONICAL_LABEL_ALIASES = {
    field: {re.sub(r"[^A-Z0-9]+", " ", alias).upper().strip() for alias in aliases}
    for field, aliases in LABEL_ALIASES.items()
}


def levenshtein_distance(a: str, b: str) -> int:
    """Return the minimum number of single-character edits needed to convert ``a`` to ``b``."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    # Keep the shorter string as the DP row to reduce memory usage.
    if len(a) < len(b):
        a, b = b, a

    previous_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current_row = [i]
        for j, char_b in enumerate(b, start=1):
            insert_cost = current_row[j - 1] + 1
            delete_cost = previous_row[j] + 1
            substitute_cost = previous_row[j - 1] + (char_a != char_b)
            current_row.append(min(insert_cost, delete_cost, substitute_cost))
        previous_row = current_row
    return previous_row[-1]


def _normalise_label(label: str) -> str:
    """Uppercase a document label and collapse punctuation into spaces."""
    return re.sub(r"[^A-Z0-9]+", " ", str(label).upper()).strip()


def _canonical_field_name(raw_label: str) -> Optional[str]:
    """Map a raw document label to its canonical comparison-field name."""
    label = _normalise_label(raw_label)
    for field, aliases in CANONICAL_LABEL_ALIASES.items():
        if label in aliases:
            return field
    return None


def _normalise_name(value: Optional[str]) -> str:
    """Normalize a name for comparison, including removal of legal-form words."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    text = re.sub(r"\(([A-Z0-9]+)\)", r" \1 ", text.upper())
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    tokens = []
    # Legal suffixes do not identify the underlying business and are ignored.
    for token in text.split():
        token = token.strip("()")
        if not token:
            continue
        if token in LEGAL_WORDS:
            continue
        tokens.append(token)
    return " ".join(tokens)


def _same_words_in_any_order(a: str, b: str) -> bool:
    """Return whether two values contain the same normalized words in any order."""
    a_words = _normalise_name(a).split()
    b_words = _normalise_name(b).split()
    if not a_words or not b_words:
        return False
    return sorted(a_words) == sorted(b_words)


def _extract_locode(value: Optional[str]) -> Optional[str]:
    """Extract a five-letter UN/LOCODE from a parenthesized value, if present."""
    if value is None:
        return None
    match = re.search(r"\(([A-Z]{5})\)", str(value).upper())
    if match:
        return match.group(1)
    return None


def _extract_number(value: Optional[str]) -> Optional[float]:
    """Extract the first integer or decimal number from a field value."""
    if value is None:
        return None
    text = str(value)
    match = re.search(r"\d[\d,]*(?:\.\d+)?", text)
    if not match:
        return None
    number_text = match.group(0).replace(",", "")
    return float(number_text)


def _port_city_name(value: Optional[str]) -> str:
    """Reduce a port value to a normalized city name for fallback comparison."""
    if value is None:
        return ""
    text = str(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)

    country_words = (
        "CHINA|SINGAPORE|MALAYSIA|INDONESIA|THAILAND|VIETNAM|JAPAN|KOREA|"
        "PHILIPPINES|USA|UK|AUSTRALIA|INDIA|BANGLADESH|PAKISTAN"
    )
    match = re.search(rf"\b(?:{country_words})\b", text)
    if match:
        before = text[:match.start()].strip()
        after = text[match.end():].strip()
        if before:
            text = before
        elif after:
            text = after

    text = re.sub(r"\s*,\s*.*$", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return _normalise_name(text)


def _compare_text_value(a: str, b: str) -> Tuple[str, float, int, str]:
    """Compare two text values and return verdict, similarity, distance, and explanation."""
    if not a or not b:
        return ("REVIEW", 0.0, 0, "A required value is missing; escalation is required.")

    left = a.strip()
    right = b.strip()
    if left == right:
        return ("MATCH", 1.0, 0, "Exact text match after trimming.")

    norm_left = _normalise_name(left)
    norm_right = _normalise_name(right)
    if norm_left == norm_right:
        return ("MATCH", 1.0, 0, "Values match after normalisation and legal-form stripping.")
    if _same_words_in_any_order(norm_left, norm_right):
        return ("MATCH", 1.0, levenshtein_distance(norm_left, norm_right), "Same words appear in a different order.")

    distance = levenshtein_distance(norm_left, norm_right)
    longer_length = max(len(norm_left), len(norm_right)) or 1
    similarity = 1.0 - (distance / longer_length)

    if similarity >= REVIEW_THRESHOLD:
        return (
            "REVIEW",
            round(similarity, 4),
            distance,
            "Similarity is high but not an exact match; a human should review this near-duplicate.",
        )

    return (
        "MISMATCH",
        round(similarity, 4),
        distance,
        "Similarity is below the review threshold, so the names do not match.",
    )


def compare_field(field_name: str, si_value: Optional[str], bl_value: Optional[str]) -> Dict[str, object]:
    """Compare one SI/BL field using text, port, or numeric matching rules."""
    if si_value is None or bl_value is None:
        return {
            "field": field_name,
            "verdict": "REVIEW",
            "similarity": 0.0,
            "distance": 0,
            "note": "A required field is missing; review is required.",
        }

    si_text = str(si_value).strip()
    bl_text = str(bl_value).strip()
    if not si_text or not bl_text:
        return {
            "field": field_name,
            "verdict": "REVIEW",
            "similarity": 0.0,
            "distance": 0,
            "note": "A required field is empty; review is required.",
        }

    if field_name in {"port_of_loading", "port_of_discharge"}:
        si_locode = _extract_locode(si_text)
        bl_locode = _extract_locode(bl_text)
        if si_locode and bl_locode:
            left_city = _port_city_name(si_text)
            right_city = _port_city_name(bl_text)
            left = _normalise_name(left_city)
            right = _normalise_name(right_city)
            if si_locode == bl_locode and left == right:
                return {
                    "field": field_name,
                    "verdict": "MATCH",
                    "similarity": 1.0,
                    "distance": 0,
                    "note": "UN/LOCODE and normalized port city both match.",
                }
            return {
                "field": field_name,
                "verdict": "MISMATCH",
                "similarity": 0.0,
                "distance": levenshtein_distance(left, right),
                "note": "Port city or UN/LOCODE differs.",
            }

        left = _port_city_name(si_text)
        right = _port_city_name(bl_text)
        comparison = _compare_text_value(left, right)
        verdict, similarity, distance, note = comparison
        return {
            "field": field_name,
            "verdict": verdict,
            "similarity": similarity,
            "distance": distance,
            "note": f"Port names compared by city only. {note}",
        }

    if field_name in {"container_count", "gross_weight_kg"}:
        si_num = _extract_number(si_text)
        bl_num = _extract_number(bl_text)
        if si_num is None or bl_num is None:
            return {
                "field": field_name,
                "verdict": "REVIEW",
                "similarity": 0.0,
                "distance": 0,
                "note": "A required numeric field is missing or unreadable; review is required.",
            }
        if si_num == bl_num:
            return {
                "field": field_name,
                "verdict": "MATCH",
                "similarity": 1.0,
                "distance": 0,
                "note": "Numeric values are equal.",
            }
        diff = abs(si_num - bl_num)
        return {
            "field": field_name,
            "verdict": "MISMATCH",
            "similarity": 0.0,
            "distance": int(diff),
            "note": "Numeric values differ.",
        }

    verdict, similarity, distance, note = _compare_text_value(si_text, bl_text)
    return {
        "field": field_name,
        "verdict": verdict,
        "similarity": similarity,
        "distance": distance,
        "note": note,
    }


def extract_fields(document_text: Optional[str]) -> Dict[str, str]:
    """Extract recognized comparison fields from a plain-text document.

    Expected format: LABEL: value
    For multi-line values, lines without a known label are appended to the current field.
    """
    if not document_text:
        return {}

    fields: Dict[str, str] = {}
    current_field = None
    
    for raw_line in str(document_text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
            
        if ":" in line:
            label_text, value_text = line.split(":", 1)
            field_name = _canonical_field_name(label_text)
            if field_name is not None:
                current_field = field_name
                value = value_text.strip()
                if value:
                    fields[current_field] = value
                continue
                
        if current_field:
            if current_field in fields:
                fields[current_field] += "\n" + line
            else:
                fields[current_field] = line
                
    return fields


def compare_document_pair(si_document: Optional[str], bl_document: Optional[str]) -> Dict[str, Dict[str, object]]:
    """Compare SI and BL text and return verdicts for every field in ``FIELD_ORDER``."""
    si_fields = extract_fields(si_document)
    bl_fields = extract_fields(bl_document)
    results: Dict[str, Dict[str, object]] = {}
    for field in FIELD_ORDER:
        if field == "description_of_goods":
            si_items = si_fields.get(field, "").split('\n')
            bl_items = bl_fields.get(field, "").split('\n')
            si_items = [x.strip() for x in si_items if x.strip()]
            bl_items = [x.strip() for x in bl_items if x.strip()]
            
            if not si_items and not bl_items:
                results[field] = {
                    "field": field,
                    "verdict": "REVIEW",
                    "similarity": 0.0,
                    "distance": 0,
                    "note": "A required field is missing; review is required.",
                    "item_results": []
                }
            elif not si_items or not bl_items:
                results[field] = {
                    "field": field,
                    "verdict": "REVIEW",
                    "similarity": 0.0,
                    "distance": 0,
                    "note": "A required field is empty; review is required.",
                    "item_results": []
                }
            else:
                item_results = item_compare.compare_items(si_items, bl_items)
                verdicts = [res['verdict'] for res in item_results]
                if 'MISMATCH' in verdicts:
                    overall = 'MISMATCH'
                elif 'REVIEW' in verdicts:
                    overall = 'REVIEW'
                else:
                    overall = 'MATCH'
                    
                results[field] = {
                    "field": field,
                    "verdict": overall,
                    "similarity": sum(r['cosine'] for r in item_results) / len(item_results) if item_results else 0.0,
                    "distance": 0,
                    "note": f"Item comparison: {len(item_results)} items processed.",
                    "item_results": item_results
                }
        else:
            results[field] = compare_field(field, si_fields.get(field), bl_fields.get(field))
    return results


def report_document_pair(si_document: Optional[str], bl_document: Optional[str]) -> Dict[str, Dict[str, object]]:
    """Print a compact SI/BL comparison report and return the field results."""
    si_fields = extract_fields(si_document)
    bl_fields = extract_fields(bl_document)
    results = compare_document_pair(si_document, bl_document)

    for field in FIELD_ORDER:
        si_value = si_fields.get(field, "")
        bl_value = bl_fields.get(field, "")
        result = results[field]
        if field == "description_of_goods":
            print(f"{field:<18} | {result['verdict']:<7} | sim={result['similarity']:.2f}")
            for itm in result.get("item_results", []):
                print(f"  -> SI: {itm['si']} | BL: {itm['bl']} | {itm['verdict']} | sim={itm['cosine']:.2f} | {itm['reason']}")
        else:
            print(
                f"{field:<18} | SI: {si_value or 'MISSING':<35} | "
                f"BL: {bl_value or 'MISSING':<35} | {result['verdict']:<7} | "
                f"sim={result['similarity']:.2f} | dist={result['distance']}"
            )

    if all(result["verdict"] == "MATCH" for result in results.values()):
        print("No mismatch detected.")
    return results


def read_text_file(path: str | Path) -> str:
    """Read a file as UTF-8 while ignoring undecodable bytes in dataset files."""
    file_path = Path(path)
    return file_path.read_text(encoding="utf-8", errors="ignore")


def compare_file_pair(si_path: str | Path, bl_path: str | Path) -> Dict[str, Dict[str, object]]:
    """Read and compare two attachment files, such as an SI and BL text file."""
    si_document = read_text_file(si_path)
    bl_document = read_text_file(bl_path)
    return compare_document_pair(si_document, bl_document)


def find_attachment_pair_for_email(email_id: str, dataset_dir: str | Path = "data_v2") -> Tuple[Path, Path]:
    """Locate and return the SI and BL attachment paths for an email record."""
    root = Path(dataset_dir)
    inbox_dir = root / "inbox"
    email_file = inbox_dir / f"{email_id}.json"
    if not email_file.exists():
        raise FileNotFoundError(f"Email metadata not found: {email_file}")

    with email_file.open("r", encoding="utf-8", errors="ignore") as fh:
        payload = json.load(fh)

    attachment_names = payload.get("attachments", [])
    if not attachment_names:
        raise ValueError(f"No attachments found for {email_id}.")

    matched_si = None
    matched_bl = None
    for attachment_name in attachment_names:
        candidate = Path(attachment_name)
        if not candidate.is_absolute():
            candidate = root / candidate
        if not candidate.exists():
            # Dataset metadata may contain only a filename, while files live in
            # the dataset's shared attachments directory.
            fallback = root / "attachments" / candidate.name
            if fallback.exists():
                candidate = fallback
        if not candidate.exists():
            continue

        lower_name = str(candidate).lower()
        if "_si" in lower_name and lower_name.endswith((".txt", ".csv", ".xlsx", ".docx", ".pdf")):
            matched_si = candidate
        elif "_bl" in lower_name and lower_name.endswith((".txt", ".csv", ".xlsx", ".docx", ".pdf")):
            matched_bl = candidate

    if matched_si is None or matched_bl is None:
        raise ValueError(f"Could not find a matching SI/BL pair for {email_id} in {root / 'attachments'}.")
    return matched_si, matched_bl


def compare_email_dataset(email_id: str, dataset_dir: str | Path = "data_v2") -> Dict[str, Dict[str, object]]:
    """Find, read, and compare the SI and BL attachments for an email record."""
    si_path, bl_path = find_attachment_pair_for_email(email_id, dataset_dir)
    return compare_file_pair(si_path, bl_path)


__all__ = [
    "FIELD_ORDER",
    "REVIEW_THRESHOLD",
    "extract_fields",
    "compare_field",
    "compare_document_pair",
    "report_document_pair",
    "read_text_file",
    "compare_file_pair",
    "find_attachment_pair_for_email",
    "compare_email_dataset",
    "levenshtein_distance",
]


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser for the comparison utility."""
    parser = argparse.ArgumentParser(description="Compare SI/BL proper-noun strings with regex + Levenshtein distance.")
    parser.add_argument("si_path", nargs="?", help="Path to the SI document or a literal email id like email_001.")
    parser.add_argument("bl_path", nargs="?", help="Path to the BL document. Optional when using --email-id.")
    parser.add_argument("--email-id", dest="email_id", help="Email id to read from the real dataset, e.g. email_001.")
    parser.add_argument("--dataset-dir", default="data_v2", help="Root dataset directory (default: data_v2).")
    return parser


def main() -> None:
    """Run the command-line comparison workflow selected by the provided arguments."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.email_id:
        results = compare_email_dataset(args.email_id, args.dataset_dir)
        for field in FIELD_ORDER:
            result = results[field]
            print(f"{field}: {result['verdict']} (sim={result['similarity']:.2f}, dist={result['distance']})")
        return

    if args.si_path and args.bl_path:
        results = compare_file_pair(args.si_path, args.bl_path)
        report_document_pair(read_text_file(args.si_path), read_text_file(args.bl_path))
        print("\nSummary:")
        for field in FIELD_ORDER:
            result = results[field]
            print(f"{field}: {result['verdict']} | sim={result['similarity']:.2f} | dist={result['distance']}")
        return

    si_path, bl_path = find_attachment_pair_for_email("email_349", "data_v2")
    report_document_pair(read_text_file(si_path), read_text_file(bl_path))


if __name__ == "__main__":
    main()
