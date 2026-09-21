"""Tuning knobs for the mail classifier. Override with environment variables."""
import os
from pathlib import Path
from .models import ClassificationConfig

def load_config() -> ClassificationConfig:
    default_embedding_path = Path(__file__).resolve().parents[1] / "models" / "all-MiniLM-L6-v2"
    default_classifier_path = Path(__file__).resolve().parents[1] / "models" / "random_forest_classifier.joblib"
    return ClassificationConfig(
        review_threshold=float(os.getenv("CLASSIFIER_REVIEW_THRESHOLD", "0.80")),
        temperature=float(os.getenv("CLASSIFIER_TEMPERATURE", "0.15")),
        embedding_model=os.getenv("EMBEDDING_MODEL", str(default_embedding_path)),
        embedding_batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "32")),
        classifier_path=Path(os.getenv("CLASSIFIER_MODEL_PATH", str(default_classifier_path))),
    )
