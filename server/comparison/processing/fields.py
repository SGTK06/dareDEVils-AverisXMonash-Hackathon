from ..processing_steps.normalization import normalize_text, levenshtein_similarity
from ..processing_steps.numbers import parse_number
from ..processing_steps.ports import parse_port


def result(field: str, verdict: str, similarity: float, note: str, **extra):
    return {"field": field, "verdict": verdict, "similarity": round(float(similarity), 4), "note": note, **extra}


def process_entity_field(field: str, left: str, right: str):
    if not left or not right:
        return result(field, "REVIEW", 0, "missing value")
    a, b = normalize_text(left), normalize_text(right)
    if a == b or sorted(a.split()) == sorted(b.split()):
        return result(field, "MATCH", 1, "normalized entity match")
    similarity = levenshtein_similarity(a, b)
    verdict = "REVIEW" if similarity >= .85 else "MISMATCH"
    return result(field, verdict, similarity, "near entity match" if verdict == "REVIEW" else "entity differs")


def process_port_field(field: str, left: str, right: str):
    if not left or not right:
        return result(field, "REVIEW", 0, "missing port value")
    left_code, left_name = parse_port(left)
    right_code, right_name = parse_port(right)
    if left_code and right_code:
        same = left_code == right_code
        return result(field, "MATCH" if same else "MISMATCH", 1 if same else 0, "same UN/LOCODE" if same else "UN/LOCODE differs")
    return process_entity_field(field, left_name, right_name)


def process_numeric_field(field: str, left: str, right: str):
    a, b = parse_number(left, field), parse_number(right, field)
    if a is None or b is None:
        return result(field, "REVIEW", 0, "missing or unreadable numeric value")
    same = a == b
    return result(field, "MATCH" if same else "MISMATCH", 1 if same else 0, "numeric values equal" if same else "numeric values differ", si_number=a, bl_number=b)


def process_field(field: str, left: str, right: str):
    if field in {"container_count", "gross_weight_kg"}:
        return process_numeric_field(field, left, right)
    if field in {"port_of_loading", "port_of_discharge"}:
        return process_port_field(field, left, right)
    return process_entity_field(field, left, right)
