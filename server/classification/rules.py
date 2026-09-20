import re

CATEGORIES = ("BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM")
PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "SPAM": (re.compile(r"prize|winner|parcel fee|mailbox full|phishing|claim your", re.I),),
    "INVOICE_QUERY": (re.compile(r"invoice|billing|local charges|freight charge|d\s*&\s*d|demurrage|total freight", re.I),),
    "SI_REQUEST": (re.compile(r"request si|si needed|cust si|shipping instruction needed|\bCUST SI\b", re.I),),
    "BL_COMPARISON": (re.compile(r"draft bl|request bl|confirm docs|check document|bl amendment|to confirm docs|bill of lading|amend bl", re.I),),
}

def text_for(email: dict) -> str:
    return f"{email.get('subject', '')}\n{email.get('body', '')}".strip()

def lexical_scores(text: str) -> dict[str, float]:
    scores = {category: 0.0 for category in CATEGORIES}
    for category, patterns in PATTERNS.items():
        # A direct intent phrase is strong evidence; the classifier still
        # normalizes competing categories and escalates ambiguous messages.
        scores[category] = min(1.0, sum(0.90 for pattern in patterns if pattern.search(text)))
    if not scores["BL_COMPARISON"] and re.search(r"\bSI\b", text, re.I) and re.search(r"\bBL\b|bill of lading", text, re.I):
        scores["BL_COMPARISON"] = 0.24
    return scores
