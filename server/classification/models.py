from dataclasses import dataclass, asdict
from typing import Any
from pathlib import Path

@dataclass(frozen=True)
class ClassificationConfig:
    review_threshold: float = 0.80
    temperature: float = 0.15
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    classifier_path: Path = Path("models/random_forest_classifier.joblib")

@dataclass
class ClassificationResult:
    category: str
    confidence: float
    scores: dict[str, float]
    check_required: bool
    review_reason: str | None = None
    provider: str = "random_forest"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
