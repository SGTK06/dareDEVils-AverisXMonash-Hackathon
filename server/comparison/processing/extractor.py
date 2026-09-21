import re

from ..processing_steps.normalization import normalize_label

FIELD_ORDER = ["shipper", "consignee", "notify_party", "port_of_loading", "port_of_discharge", "container_count", "gross_weight_kg"]
ALIASES = {
    "shipper": {"SHIPPER", "SHIPPER EXPORTER", "SHIPPER PRINCIPAL OR SELLER", "EXPORTER"},
    "consignee": {"CONSIGNEE", "CONSIGNEE NON NEGOTIABLE", "TO THE ORDER OF", "TO THE ORDER OF SHIPPER"},
    "notify_party": {"NOTIFY", "NOTIFY PARTY", "NOTIFY PARTY INTERMEDIATE CONSIGNEE", "INTERMEDIATE CONSIGNEE"},
    "port_of_loading": {"PORT OF LOADING", "PORT OF LOADING POL", "LOAD PORT", "LOAD PORT POL", "POL"},
    "port_of_discharge": {"PORT OF DISCHARGE", "PORT OF DISCHARGE POD", "DISCHARGE PORT", "DISCHARGE PORT POD", "POD"},
    "container_count": {"CONTAINER COUNT", "TOTAL CONTAINERS", "NUMBER OF CONTAINERS", "NO OF CONTAINERS", "NO OF CONTAINERS OR PACKAGES", "NO CONTAINERS"},
    "gross_weight_kg": {"GROSS WEIGHT", "GROSS WEIGHT KG", "GROSS WEIGHT (KG)", "GROSS WT KG", "GROSS WT KGS", "GROSS WT (KGS)", "GROSS WT (KG)"},
}
ALIASES = {field: {normalize_label(alias) for alias in labels} for field, labels in ALIASES.items()}


def field_for_label(label: str) -> str | None:
    normalized = normalize_label(label)
    return next((field for field, labels in ALIASES.items() if normalized in labels), None)


def extract_fields(text: str | None) -> dict[str, str]:
    values: dict[str, str] = {}
    current: str | None = None
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" in line or "|" in line:
            delimiter = ":" if ":" in line else "|"
            label, value = line.split(delimiter, 1)
            field = field_for_label(label)
            if field:
                current = field
                if value.strip():
                    values[field] = value.strip()
            else:
                current = None
            continue
        if current:
            values[current] = f"{values.get(current, '')} {line}".strip()
    return values
