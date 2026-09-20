import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------

SERVER_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(SERVER_ROOT / ".env.local")

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing from server/.env.local"
    )


client = genai.Client(api_key=API_KEY)


# ---------------------------------------------------------
# The seven fields required by the hackathon
# ---------------------------------------------------------

SHIPMENT_FIELDS = [
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
]


# ---------------------------------------------------------
# Prompt
# ---------------------------------------------------------

EXTRACTION_PROMPT = """
You are extracting shipping information from a shipping document.

Extract these seven fields:

1. shipper
2. consignee
3. notify_party
4. port_of_loading
5. port_of_discharge
6. container_count
7. gross_weight_kg

Different labels can refer to the same field.

Examples:

"Load Port", "Loading Port", "POL"
    -> port_of_loading

"Discharge Port", "POD"
    -> port_of_discharge

"Total Containers", "Container Qty"
    -> container_count

"Gross Weight", "Gross Wt", "Total Gross Weight"
    -> gross_weight_kg

Return ONLY valid JSON.

Use this structure:

{
    "shipper": {
        "value": "...",
        "confidence": 0.0,
        "evidence": "..."
    },
    "consignee": {
        "value": "...",
        "confidence": 0.0,
        "evidence": "..."
    },
    "notify_party": {
        "value": "...",
        "confidence": 0.0,
        "evidence": "..."
    },
    "port_of_loading": {
        "value": "...",
        "confidence": 0.0,
        "evidence": "..."
    },
    "port_of_discharge": {
        "value": "...",
        "confidence": 0.0,
        "evidence": "..."
    },
    "container_count": {
        "value": 0,
        "confidence": 0.0,
        "evidence": "..."
    },
    "gross_weight_kg": {
        "value": 0,
        "confidence": 0.0,
        "evidence": "..."
    }
}

Rules:

- Do not invent missing values.
- If a field is missing, use null.
- Confidence must be between 0 and 1.
- Evidence should quote or closely identify the relevant source text.
- container_count must be an integer.
- gross_weight_kg must be a number in kilograms.
- Normalize obvious formatting differences such as:
  "22,000 KGS" -> 22000
  "22000 KG" -> 22000
  "3 Containers" -> 3
"""


# ---------------------------------------------------------
# Gemini extraction
# ---------------------------------------------------------

def extract_with_gemini(document_text: str) -> dict:
    """
    Use Gemini as the fallback document extractor.

    Args:
        document_text: Text extracted from the document.

    Returns:
        Dictionary containing the seven shipment fields.
    """

    if not document_text or not document_text.strip():
        raise ValueError("Cannot send empty document to Gemini")

    prompt = f"""
{EXTRACTION_PROMPT}

DOCUMENT:

--------------------
{document_text}
--------------------
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "temperature": 0,
            "response_mime_type": "application/json",
        },
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response")

    try:
        result = json.loads(response.text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Gemini returned invalid JSON: {response.text}"
        ) from e

    return result


# ---------------------------------------------------------
# Confidence check
# ---------------------------------------------------------

def needs_human_review(result: dict) -> bool:
    """
    Decide whether Gemini's extraction is reliable enough
    to continue automatically.
    """

    for field in SHIPMENT_FIELDS:

        field_data = result.get(field)

        if not field_data:
            return True

        value = field_data.get("value")
        confidence = field_data.get("confidence", 0)

        # Missing required value
        if value is None:
            return True

        # Low confidence
        if confidence < 0.80:
            return True

    return False


# ---------------------------------------------------------
# Test
# ---------------------------------------------------------

if __name__ == "__main__":

    test_document = """
    SHIPPING INSTRUCTION

    Shipper: ABC Logistics Ltd
    Consignee: Melbourne Imports Pty Ltd
    Notify Party: Melbourne Imports Pty Ltd

    Port of Loading: Port Klang
    Port of Discharge: Melbourne

    Container Count: 3
    Gross Weight: 22,000 KGS
    """

    result = extract_with_gemini(test_document)

    print(json.dumps(result, indent=2))

    if needs_human_review(result):
        print("\nREVIEW REQUIRED")
    else:
        print("\nExtraction confident enough to continue")
