"""Configurable, deterministic mail intent classification extracted from the notebook."""
from .config import load_config
from .models import ClassificationConfig, ClassificationResult
from .rules import CATEGORIES, has_bl_si_comparison, is_standalone_bl_request, lexical_scores, text_for

class MailClassifier:
    def __init__(self, config: ClassificationConfig | None = None):
        self.config = config or load_config()
        self._nlp = None
        self._category_docs = None

    def _load_spacy(self):
        if self._nlp is None:
            import spacy
            self._nlp = spacy.load(self.config.spacy_model)
            descriptions = {
                "BL_COMPARISON": "Comparison requested for the Bill of Lading (BL) and Shipping Instruction (SI)",
                "SI_REQUEST": "Request for a new Shipping Instruction (SI)",
                "INVOICE_QUERY": "Query about an invoice, billing, or charges",
                "GENERAL": "General business message or operational update",
                "SPAM": "Unwanted marketing, phishing, or fraudulent message",
            }
            self._category_docs = {label: self._nlp(description) for label, description in descriptions.items()}
        return self._nlp, self._category_docs

    def classify(self, email: dict) -> ClassificationResult:
        text = text_for(email)
        if not text:
            return ClassificationResult("GENERAL", 0.0, {c: 0.0 for c in CATEGORIES}, True, "empty_message")
        nlp, category_docs = self._load_spacy()
        document = nlp(text)
        similarities = {label: float(document.similarity(category_doc)) for label, category_doc in category_docs.items()}
        lexical = lexical_scores(text)
        if not has_bl_si_comparison(text):
            lexical["BL_COMPARISON"] = 0.0
        combined = {label: similarities[label] + lexical[label] for label in CATEGORIES}
        if not has_bl_si_comparison(text):
            combined["BL_COMPARISON"] = -1e6
        if is_standalone_bl_request(text):
            combined["GENERAL"] = max(combined.values()) + 1.0
        category = max(combined, key=combined.get)
        confidence = similarities[category]
        return ClassificationResult(category, confidence, similarities, confidence < self.config.review_threshold, "low_spacy_similarity" if confidence < self.config.review_threshold else None, "spacy")

    def classify_with_fallback(self, email: dict) -> ClassificationResult:
        try:
            primary = self.classify(email)
        except Exception as exc:
            primary = ClassificationResult("GENERAL", 0.0, {}, True, f"spacy_failed: {exc}", "spacy_failed")
        if not primary.check_required:
            return primary
        try:
            from llm.classification import verify_classification
            verified = verify_classification(email.get("subject", ""), email.get("body", ""))
            confidence = verified["confidence"]
            return ClassificationResult(
                category=verified["category"], confidence=confidence,
                scores={verified["category"]: confidence},
                check_required=confidence < self.config.review_threshold,
                review_reason="low_llm_confidence" if confidence < self.config.review_threshold else None,
                provider="gemini",
            )
        except Exception as exc:
            return ClassificationResult(
                category=primary.category, confidence=primary.confidence,
                scores=primary.scores, check_required=True,
                review_reason=f"llm_verification_failed: {exc}", provider="primary+gemini_failed",
            )

    def classify_many(self, emails: list[dict]) -> list[ClassificationResult]:
        return [self.classify(email) for email in emails]
