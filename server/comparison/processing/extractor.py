import re
from collections import Counter
from ..processing_steps.normalization import normalize_label
from ..processing_steps.semantic_matching import semantic_field_match

FIELD_ORDER = ["shipper", "consignee", "notify_party", "port_of_loading", "port_of_discharge", "container_count", "gross_weight_kg"]
FIELD_PROTOTYPES_FALLBACK = {
    "shipper": "shipper exporter seller", "consignee": "consignee order receiver",
    "notify_party": "notify party intermediate consignee", "port_of_loading": "port loading origin",
    "port_of_discharge": "port discharge destination", "container_count": "container count number packages",
    "gross_weight_kg": "gross weight kilograms",
}
ALIASES = {
    "shipper": {"SHIPPER", "SHIPPER EXPORTER", "SHIPPER PRINCIPAL OR SELLER", "EXPORTER"},
    "consignee": {"CONSIGNEE", "CONSIGNEE NON NEGOTIABLE", "TO THE ORDER OF", "TO THE ORDER OF SHIPPER"},
    "notify_party": {"NOTIFY", "NOTIFY PARTY", "NOTIFY PARTY INTERMEDIATE CONSIGNEE", "INTERMEDIATE CONSIGNEE"},
    "port_of_loading": {"PORT OF LOADING", "PORT OF LOADING POL", "LOAD PORT", "LOAD PORT POL", "POL"},
    "port_of_discharge": {"PORT OF DISCHARGE", "PORT OF DISCHARGE POD", "DISCHARGE PORT", "DISCHARGE PORT POD", "POD"},
    "container_count": {"CONTAINER COUNT", "TOTAL CONTAINERS", "NUMBER OF CONTAINERS", "NO OF CONTAINERS", "NO OF CONTAINERS OR PACKAGES", "NO CONTAINERS"},
    "gross_weight_kg": {"GROSS WEIGHT", "GROSS WEIGHT KG", "GROSS WEIGHT KGS", "GROSS WEIGHT KGS KGS", "GROSS WEIGHT (KG)", "GROSS WT KG", "GROSS WT KGS", "GROSS WT (KGS)", "GROSS WT (KG)"},
}
ALIASES = {field: {normalize_label(alias) for alias in labels} for field, labels in ALIASES.items()}
def field_for_label(label: str) -> str | None:
    normalized = normalize_label(label)
    exact = next((field for field, labels in ALIASES.items() if normalized in labels), None)
    if exact:
        return exact
    # PDF/DOCX renderers may append translated labels or unit annotations.
    # Accept only a known alias followed by label metadata, never arbitrary
    # substring matches.
    for field, labels in ALIASES.items():
        if any(normalized.startswith(alias + " ") for alias in labels):
            return field
    # Notebook-compatible embedding + clustering fallback for unfamiliar
    # labels. Exact aliases above always win, preserving existing accuracy.
    # Semantic embeddings are deliberately high precision.  At this threshold
    # they can only override the legacy fallback when the label is extremely
    # close to a canonical field; uncertain labels retain the old behavior.
    semantic_field, semantic_score = semantic_field_match(normalized, .80)
    if semantic_field:
        return semantic_field

    # Keep the previous offline behavior when the local embedding model is
    # unavailable or cannot initialize. This is also conservative: token
    # overlap is accepted only at the same threshold used by the old path.
    expanded = normalized.lower()
    left = Counter(expanded.split())
    candidates = []
    for field, prototype in FIELD_PROTOTYPES_FALLBACK.items():
        right = Counter(prototype.split())
        denominator = (sum(v * v for v in left.values()) * sum(v * v for v in right.values())) ** .5
        score = sum(left[key] * right[key] for key in set(left) | set(right)) / denominator if denominator else 0.0
        candidates.append((score, field))
    score, field = max(candidates)
    return field if score >= .42 else None


def extract_fields(text: str | None) -> dict[str, str]:
    values: dict[str, str] = {}
    current: str | None = None
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" in line or "|" in line:
            delimiters = [position for position in (line.find(":"), line.find("|")) if position >= 0]
            delimiter_position = min(delimiters)
            label, value = line[:delimiter_position], line[delimiter_position + 1:]
            field = field_for_label(label)
            if field:
                current = field
                if value.strip():
                    values[field] = value.strip()
            else:
                current = None
            continue
        standalone_field = field_for_label(line)
        if standalone_field:
            current = standalone_field
            continue
        if current:
            values[current] = f"{values.get(current, '')} {line}".strip()
    return values
