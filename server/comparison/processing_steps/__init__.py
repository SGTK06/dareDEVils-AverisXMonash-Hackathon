"""Small, reusable comparison primitives."""

from .documents import document_text
from .normalization import normalize_label, normalize_text, levenshtein_similarity
from .numbers import parse_number
from .ports import parse_port

__all__ = ["document_text", "normalize_label", "normalize_text", "levenshtein_similarity", "parse_number", "parse_port"]
