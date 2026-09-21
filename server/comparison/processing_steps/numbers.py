import re

UNIT_FACTORS = {"kg": 1.0, "kgs": 1.0, "g": .001, "lb": .453592, "lbs": .453592, "ton": 1000.0, "tons": 1000.0}


def parse_number(value: str, field: str) -> float | None:
    text = str(value or "").upper().replace(",", "")
    if field == "container_count":
        match = re.search(r"(?<![A-Z0-9])\d+(?:\.\d+)?(?=\s*(?:X|PCS?|SETS?|CONTAINERS?|PACKAGES?)\b|\s*[Xx])", text)
        return float(match.group()) if match else None
    matches = list(re.finditer(r"([-+]?\d+(?:\.\d+)?)\s*(KG|KGS|G|LB|LBS|TONS?|T)?\b", text))
    if not matches:
        return None
    weighted = [match for match in matches if match.group(2)]
    match = weighted[-1] if weighted else matches[-1]
    return float(match.group(1)) * UNIT_FACTORS.get((match.group(2) or "KG").lower(), 1.0)
