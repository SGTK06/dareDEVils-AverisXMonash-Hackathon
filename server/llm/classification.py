"""Optional Gemini verification for low-confidence mail intent decisions."""
import json
import os
from google import genai

CATEGORIES = ("BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM")

def verify_classification(subject: str, body: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    client = genai.Client(api_key=api_key)
    prompt = f"""Classify this shipping operations email into exactly one category: {', '.join(CATEGORIES)}.
Return only JSON: {{\"category\": \"BL_COMPARISON\", \"confidence\": 0.0, \"reason\": \"short evidence\"}}.
Confidence must be a number from 0 to 1 and reflect your uncertainty. Do not invent facts.
SUBJECT: {subject}\nBODY: {body}"""
    response = client.models.generate_content(
        model=os.getenv("GEMINI_CLASSIFICATION_MODEL", "gemini-2.5-flash"),
        contents=prompt,
        config={"temperature": 0, "response_mime_type": "application/json"},
    )
    result = json.loads(response.text or "")
    category = result.get("category")
    confidence = float(result.get("confidence", 0))
    if category not in CATEGORIES or not 0 <= confidence <= 1:
        raise ValueError("Gemini returned an invalid classification result")
    return {"category": category, "confidence": confidence, "reason": result.get("reason")}
