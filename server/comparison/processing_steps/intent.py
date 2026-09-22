"""Semantic intent routing for comparison requests without two documents."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np

INTENT_PROTOTYPES = {
    "pending_draft_request": [
        "Please send the draft BL for checking.",
        "Kindly provide the draft bill of lading for review.",
        "We are waiting for the draft BL to be sent.",
        "Please assist to send the draft BL for checking asap.",
    ],
    "missing_comparison_document": [
        "Please compare the SI and draft BL, but the attachments are missing.",
        "The draft BL is still missing from this comparison request.",
        "The attachments were dropped; compare the shipping instruction and bill of lading.",
        "Compare the SI and draft BL and confirm, but the documents were not attached.",
    ],
}


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    default_path = Path(__file__).resolve().parents[3] / "models" / "all-MiniLM-L6-v2"
    model_name = os.environ.get("EMBEDDING_MODEL", str(default_path))
    return SentenceTransformer(model_name, device="cpu")


@lru_cache(maxsize=1)
def _prototype_vectors():
    model = _model()
    names = tuple(INTENT_PROTOTYPES)
    vectors = []
    for name in names:
        examples = INTENT_PROTOTYPES[name]
        encoded = model.encode(examples, normalize_embeddings=True)
        vectors.append(np.mean(encoded, axis=0))
    vectors = np.asarray(vectors)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return names, vectors


def classify_missing_attachment_intent(subject: str, body: str) -> dict[str, object]:
    """Classify the intent of a comparison email that lacks two attachments.

    A low score or small margin is deliberately routed to review rather than
    guessing between a future-BL request and a failed comparison package.
    """
    # Score focused message views as well as the complete message.  Signatures,
    # disclaimers and quoted thread history can otherwise dilute the intent.
    views = [
        str(subject or "").strip(),
        str(body or "").strip()[:1600],
        f"Subject: {subject}\nBody: {body}".strip(),
    ]
    views = [view for view in views if view]
    try:
        model = _model()
        messages = model.encode(views, normalize_embeddings=True)
        names, prototypes = _prototype_vectors()
        # Max pooling keeps a decisive sentence visible even in a long thread.
        scores = np.max(prototypes @ messages.T, axis=1)
        order = np.argsort(scores)[::-1]
        best, second = int(order[0]), int(order[1])
        confidence = float(scores[best])
        margin = float(scores[best] - scores[second])
        # The focused subject/body view produces lower absolute cosine values
        # than the full message, so use the margin as the primary safeguard.
        intent = names[best] if confidence >= 0.45 and margin >= 0.035 else "ambiguous"
        return {"intent": intent, "confidence": round(confidence, 4), "margin": round(margin, 4), "scores": {names[i]: round(float(scores[i]), 4) for i in range(len(names))}, "provider": "sentence-transformer"}
    except Exception as exc:
        return {"intent": "ambiguous", "confidence": 0.0, "margin": 0.0, "scores": {}, "provider": "unavailable", "error": str(exc)}
