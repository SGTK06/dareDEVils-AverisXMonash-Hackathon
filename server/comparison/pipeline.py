from typing import Any

from .processing import FIELD_ORDER, extract_fields, process_field


def compare_documents(si_fields: dict[str, str], bl_fields: dict[str, str]) -> dict[str, dict[str, Any]]:
    return {field: process_field(field, si_fields.get(field, ""), bl_fields.get(field, "")) for field in FIELD_ORDER}
