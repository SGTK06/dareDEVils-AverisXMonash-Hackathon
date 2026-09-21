import re

PORT_NOISE = {"PORT", "HARBOUR", "HARBOR", "TERMINAL", "CONTAINER", "INTERNATIONAL", "THE", "OF", "MALAYSIA", "SINGAPORE", "PERU", "CHINA", "INDIA", "KOREA"}


def parse_port(value: str) -> tuple[str | None, str]:
    text = str(value or "").upper()
    code_match = re.search(r"\(([A-Z]{5})\)", text)
    code = code_match.group(1) if code_match else None
    text = re.sub(r"\([A-Z]{5}\)", " ", text)
    tokens = [token for token in re.sub(r"[^A-Z0-9]+", " ", text).split() if token not in PORT_NOISE]
    return code, " ".join(tokens)
