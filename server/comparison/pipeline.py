from typing import Any

from .processing import FIELD_ORDER, extract_fields, process_field


def compare_documents(si_text: str, bl_text: str) -> dict[str, dict[str, Any]]:
    si_fields, bl_fields = extract_fields(si_text), extract_fields(bl_text)
    return {field: process_field(field, si_fields.get(field, ""), bl_fields.get(field, "")) for field in FIELD_ORDER}
