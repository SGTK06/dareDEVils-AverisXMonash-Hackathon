import re

CATEGORIES = ("BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM")
PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "SPAM": (re.compile(r"prize|winner|parcel fee|mailbox full|phishing|claim your", re.I),),
    "INVOICE_QUERY": (re.compile(r"invoice|billing|local charges|freight charge|d\s*&\s*d|demurrage|total freight", re.I),),
    "SI_REQUEST": (re.compile(r"request si|si needed|cust si|shipping instruction needed|\bCUST SI\b", re.I),),
    "BL_COMPARISON": (re.compile(r"draft bl|request bl|confirm docs|check document|bl amendment|to confirm docs|bill of lading|amend bl", re.I),),
}

def text_for(email: dict) -> str:
    attachments = email.get("attachments", []) or []
    if not isinstance(attachments, list):
        attachments = [attachments]
    return " ".join(str(value) for value in [email.get("from", ""), email.get("subject", ""), email.get("body", ""), *attachments] if value).strip()

LEXICAL_RULES = {
    "BL_COMPARISON": {"compare bl and si": 4.0, "compare the bl and si": 4.0, "compare si and bl": 4.0, "bl against the si": 4.0, "si against the bl": 4.0, "draft bl against the si": 4.0, "bl and si": 3.0},
    "SI_REQUEST": {"request si": 3.0, "shipping instruction for": 3.0, "si needed": 3.0, "cust si": 3.0, "latest si": 2.0, "please find shipping instruction": 3.0},
    "INVOICE_QUERY": {"invoice": 2.0, "billing": 2.0, "local charge": 2.5, "d & d": 2.5, "detention charge": 2.5, "missing gr": 3.0, "cancel invoice": 3.0, "payment": 1.5},
    "GENERAL": {"update summary": 3.0, "berthing report": 3.0, "outstanding bl": 3.0, "rpa": 2.5, "automated notification": 2.5, "reminder": 1.5, "time off request": 2.0},
    "SPAM": {"claim now": 3.0, "to claim": 2.5, "you have won": 3.0, "prize": 2.5, "short survey": 2.5, "gift card": 3.0, "click here": 2.5, "limited time offer": 3.0, "90% off": 3.0, "bitcoin": 3.0, "customs fee": 3.0, "verify your account": 3.0, "storage limit": 2.5},
}

def lexical_scores(text: str) -> dict[str, float]:
    lowered = text.lower()
    return {label: sum(weight for phrase, weight in rules.items() if phrase in lowered) for label, rules in LEXICAL_RULES.items()}

def has_bl_si_comparison(text: str) -> bool:
    lowered = text.lower()
    mentions_bl = bool(re.search(r"\bbl\b", lowered)) or "bill of lading" in lowered
    mentions_si = bool(re.search(r"\bsi\b", lowered)) or "shipping instruction" in lowered
    return mentions_bl and mentions_si and any(word in lowered for word in ("compare", "comparison", "check", "confirm", "verify"))

def is_standalone_bl_request(text: str) -> bool:
    lowered = text.lower()
    mentions_bl = bool(re.search(r"\bbl\b", lowered)) or "bill of lading" in lowered
    mentions_si = bool(re.search(r"\bsi\b", lowered)) or "shipping instruction" in lowered
    return mentions_bl and not mentions_si and any(phrase in lowered for phrase in ("draft bl", "amend bl", "confirm bl", "send draft bl", "check draft bl"))

