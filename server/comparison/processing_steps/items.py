"""Notebook-compatible item matching diagnostics.

Item results are deliberately kept separate from the seven contractual fields.
They are exposed to the UI and review workflow, but do not change the legacy
status decision until the dataset contract explicitly scores item defects.
"""

from __future__ import annotations

import itertools
import re
from typing import Any

ITEM_LABELS = {"description", "item", "goods", "commodity", "product", "cargo", "marks and numbers"}
NUMBER_UNIT = re.compile(r"(?P<number>\d+(?:[.,]\d+)?)\s*(?P<unit>mm|cm|m|ft|feet|in|inch|inches|kg|kgs|g|lb|lbs|ton|tons|cbm|m3|pieces|pcs|sets?)?", re.I)
FEATURES = {"ivory", "black", "white", "coated", "wooden", "steel", "aluminium", "aluminum", "red", "blue", "long"}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).lower())


def cosine_matrix(left: list[str], right: list[str]) -> list[list[float]]:
    vocab = sorted(set(itertools.chain.from_iterable(_tokens(x) for x in left + right)))
    if not vocab:
        return [[0.0 for _ in right] for _ in left]

    def vector(value: str) -> list[float]:
        values = [float(_tokens(value).count(token)) for token in vocab]
        norm = sum(item * item for item in values) ** 0.5
        return [item / norm for item in values] if norm else values

    vectors_left, vectors_right = [vector(x) for x in left], [vector(x) for x in right]
    return [[sum(a * b for a, b in zip(x, y)) for y in vectors_right] for x in vectors_left]


def aggregate_similar_items(items: list[str], threshold: float = .35) -> list[list[str]]:
    """Group semantically close descriptions using the notebook's connected components."""
    values = [str(x).strip() for x in items if str(x).strip()]
    if not values:
        return []
    scores = cosine_matrix(values, values)
    groups, seen = [], set()
    for index in range(len(values)):
        if index in seen:
            continue
        stack, group = [index], []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            group.append(values[current])
            stack.extend(j for j, score in enumerate(scores[current]) if j not in seen and score >= threshold)
        groups.append(group)
    return groups


def extract_items(text: str | None) -> list[str]:
    """Extract item-description continuation lines from plain extracted text."""
    items: list[str] = []
    active = False
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = re.split(r"[:|]", line, maxsplit=1)
        if len(parts) == 2:
            label, value = parts[0].strip(), parts[1].strip()
            active = label.casefold() in ITEM_LABELS
            if active and value:
                items.append(value)
            continue
        if active:
            # Stop at the next recognizable field-style label.
            if line.casefold() in ITEM_LABELS:
                continue
            items.append(line)
    return items


def _unit_value(number: str, unit: str | None) -> tuple[float, str]:
    factors = {"mm": .001, "cm": .01, "m": 1, "ft": .3048, "feet": .3048,
               "in": .0254, "inch": .0254, "inches": .0254, "kg": 1, "kgs": 1,
               "g": .001, "lb": .453592, "lbs": .453592, "ton": 1000, "tons": 1000,
               "cbm": 1, "m3": 1}
    normalized = (unit or "").lower()
    return float(number.replace(",", "")) * factors.get(normalized, 1), normalized


def item_signature(text: str) -> dict[str, Any]:
    numbers = []
    for match in NUMBER_UNIT.finditer(str(text)):
        value, unit = _unit_value(match.group("number"), match.group("unit"))
        numbers.append((round(value, 6), unit or "unitless"))
    words = set(_tokens(text))
    return {"numbers": numbers, "features": sorted(words & FEATURES)}


def compare_items(si_items: list[str], bl_items: list[str], threshold: float = .35) -> list[dict[str, Any]]:
    left = [str(x).strip() for x in si_items if str(x).strip()]
    right = [str(x).strip() for x in bl_items if str(x).strip()]
    if not left and not right:
        return []
    scores = cosine_matrix(left, right) if left and right else []
    pairs, used = [], set()
    for index, si_item in enumerate(left):
        candidates = sorted(((scores[index][j], j) for j in range(len(right)) if j not in used), reverse=True)
        if not candidates:
            pairs.append({"si": si_item, "bl": None, "cosine": 0.0, "verdict": "MISMATCH", "reason": "item missing from BL"})
            continue
        score, match_index = candidates[0]
        used.add(match_index)
        si_signature, bl_signature = item_signature(si_item), item_signature(right[match_index])
        reasons = []
        if si_signature["features"] != bl_signature["features"]:
            reasons.append("product features differ")
        if si_signature["numbers"] != bl_signature["numbers"]:
            reasons.append("quantities/dimensions/units differ")
        verdict = "MATCH" if score >= threshold and not reasons else "MISMATCH"
        pairs.append({"si": si_item, "bl": right[match_index], "cosine": round(float(score), 3),
                      "verdict": verdict, "reason": "; ".join(reasons)})
    for index, bl_item in enumerate(right):
        if index not in used:
            pairs.append({"si": None, "bl": bl_item, "cosine": 0.0, "verdict": "MISMATCH", "reason": "item missing from SI"})
    return pairs
