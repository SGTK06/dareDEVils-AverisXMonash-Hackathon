"""Document extraction and field-level comparison processors."""

from .extractor import FIELD_ORDER, extract_fields
from .fields import process_field

__all__ = ["FIELD_ORDER", "extract_fields", "process_field"]
