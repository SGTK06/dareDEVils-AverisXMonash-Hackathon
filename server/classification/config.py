"""Tuning knobs for the mail classifier. Override with environment variables."""
import os
from .models import ClassificationConfig

def load_config() -> ClassificationConfig:
    return ClassificationConfig(
        review_threshold=float(os.getenv("CLASSIFIER_REVIEW_THRESHOLD", "0.80")),
        temperature=float(os.getenv("CLASSIFIER_TEMPERATURE", "0.15")),
    )
