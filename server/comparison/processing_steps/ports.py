import re

PORT_NOISE = {"PORT", "HARBOUR", "HARBOR", "TERMINAL", "CONTAINER", "INTERNATIONAL", "THE", "OF", "MALAYSIA", "SINGAPORE", "PERU", "CHINA", "INDIA", "KOREA"}


def parse_port(value: str) -> tuple[str | None, str]:
    original = str(value or "").upper()
    text = original
    text = re.split(r"\b(?:OCEAN VESSEL|EXPORT CARRIER|CONTAINER NO\.?|DESCRIPTION)\b", text, maxsplit=1)[0]
    code_match = re.search(r"\(([A-Z]{5})\)", text)
    code = code_match.group(1) if code_match else None
    text = re.sub(r"\([A-Z]{5}\)", " ", text)
    tokens = [token for token in re.sub(r"[^A-Z0-9]+", " ", text).split() if token not in PORT_NOISE]
    if not tokens:
        # A country can itself be the complete port value, e.g. SINGAPORE.
        fallback = re.sub(r"\([A-Z]{5}\)", " ", original)
        tokens = re.sub(r"[^A-Z0-9]+", " ", fallback).split()
    return code, " ".join(tokens)
