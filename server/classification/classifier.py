"""Persisted Sentence Transformer + Random Forest mail classifier."""
from .config import load_config
from .embeddings import SentenceEmbeddingService
from .ml_model import RandomForestMailModel
from .models import ClassificationConfig, ClassificationResult
from .preprocessing import preprocess_email

class MailClassifier:
    def __init__(self, config: ClassificationConfig | None = None):
        self.config = config or load_config()
        self._embeddings = SentenceEmbeddingService(self.config.embedding_model)
        self._model = RandomForestMailModel(self.config.classifier_path)

    def classify(self, email: dict) -> ClassificationResult:
        text = preprocess_email(email)
        if not text:
            return ClassificationResult("GENERAL", 0.0, {}, True, "empty_message", "random_forest")
        category, confidence, scores = self._model.predict(self._embeddings.encode([text]))
        review = confidence < self.config.review_threshold
        return ClassificationResult(category, confidence, scores, review,
                                    "low_model_confidence" if review else None, "random_forest")

    def classify_with_fallback(self, email: dict) -> ClassificationResult:
        return self.classify(email)

    def classify_many(self, emails: list[dict]) -> list[ClassificationResult]:
        return [self.classify(email) for email in emails]
