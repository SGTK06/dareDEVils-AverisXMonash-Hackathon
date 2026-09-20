from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class ClassificationConfig:
    review_threshold: float = 0.80
    temperature: float = 0.15

@dataclass
class ClassificationResult:
    category: str
    confidence: float
    scores: dict[str, float]
    check_required: bool
    review_reason: str | None = None
    provider: str = "rules"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
