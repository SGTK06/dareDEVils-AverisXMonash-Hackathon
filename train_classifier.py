"""Train and persist the email Random Forest used by the API.

Run from the repository root after installing sentence-transformers,
scikit-learn, and joblib: ``python train_classifier.py``.
"""
import json
from pathlib import Path
import numpy as np
import joblib
from sentence_transformers import SentenceTransformer
from sklearn.ensemble import RandomForestClassifier
from server.classification.preprocessing import preprocess_email

ROOT = Path(__file__).parent
DATA = ROOT / "data_v2"
OUT = ROOT / "models" / "random_forest_classifier.joblib"

def main():
    truth = json.loads((DATA / "ground_truth.json").read_text(encoding="utf-8"))
    rows = []
    for path in sorted((DATA / "inbox").glob("*.json")):
        email = json.loads(path.read_text(encoding="utf-8"))
        rows.append((email, truth[email["email_id"]]["category"]))
    groups = {}
    for email, label in rows:
        groups.setdefault(label, []).append((email, label))
    # Equal-count training data: 40% of the smallest class, deterministic.
    n_train = int(np.floor(min(map(len, groups.values())) * 0.40))
    train = []
    for label in sorted(groups):
        rng = np.random.default_rng(42)
        selected = rng.choice(len(groups[label]), n_train, replace=False)
        train.extend(groups[label][i] for i in selected)
    model = SentenceTransformer(str(ROOT / "models" / "all-MiniLM-L6-v2"))
    X = model.encode([preprocess_email(email) for email, _ in train], normalize_embeddings=True, show_progress_bar=True)
    y = [label for _, label in train]
    classifier = RandomForestClassifier(n_estimators=500, max_features="sqrt", class_weight="balanced", random_state=42, n_jobs=-1)
    classifier.fit(X, y)
    OUT.parent.mkdir(exist_ok=True)
    joblib.dump(classifier, OUT)
    print(f"saved {OUT} ({len(train)} records; {n_train} per class)")

if __name__ == "__main__":
    main()
