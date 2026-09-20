"""Configurable, deterministic mail intent classification extracted from the notebook."""
import math
from .config import load_config
from .models import ClassificationConfig, ClassificationResult
from .rules import CATEGORIES, lexical_scores, text_for

class MailClassifier:
    def __init__(self, config: ClassificationConfig | None = None):
        self.config = config or load_config()

    def classify(self, email: dict) -> ClassificationResult:
        text = text_for(email)
        lexical = lexical_scores(text)
        if not text:
            return ClassificationResult("GENERAL", 0.0, {c: 0.0 for c in CATEGORIES}, True, "empty_message")
        peak = max(lexical.values())
        if peak == 0:
            scores = {c: 1 / len(CATEGORIES) for c in CATEGORIES}
        else:
            exps = {c: math.exp((value - peak) / self.config.temperature) for c, value in lexical.items()}
            total = sum(exps.values())
            scores = {c: value / total for c, value in exps.items()}
        category = max(scores, key=scores.get)
        confidence = scores[category]
        return ClassificationResult(category, confidence, scores, confidence < self.config.review_threshold, "low_classification_confidence" if confidence < self.config.review_threshold else None)

    def classify_many(self, emails: list[dict]) -> list[ClassificationResult]:
        return [self.classify(email) for email in emails]
