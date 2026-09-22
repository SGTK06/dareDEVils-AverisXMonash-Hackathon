"""Notebook-compatible semantic matching for previously unseen field labels."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np

FIELD_PROTOTYPES = {
    "shipper": "shipper exporter seller",
    "consignee": "consignee order receiver",
    "notify_party": "notify party intermediate consignee",
    "port_of_loading": "port loading load port origin",
    "port_of_discharge": "port discharge discharge port destination",
    "container_count": "container count number containers packages",
    "gross_weight_kg": "gross weight gross wt kilograms kg",
}
LABEL_EXPANSIONS = {
    "WT": "WEIGHT", "WGT": "WEIGHT", "KGS": "KILOGRAMS", "KG": "KILOGRAMS",
    "NO": "NUMBER", "NOS": "NUMBERS", "PKG": "PACKAGE", "PKGS": "PACKAGES",
    "CONT": "CONTAINER", "CONTS": "CONTAINERS", "CNTR": "CONTAINER",
    "DISCH": "DISCHARGE", "LOAD": "LOADING", "POL": "PORT LOADING", "POD": "PORT DISCHARGE",
    "CONS": "CONSIGNEE", "NOTFY": "NOTIFY", "SHPR": "SHIPPER", "EXP": "EXPORTER",
}


def expand_label(label: str) -> str:
    words = "".join(ch if ch.isalnum() else " " for ch in str(label).upper()).split()
    return " ".join(LABEL_EXPANSIONS.get(word, word) for word in words)


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    default = Path(__file__).resolve().parents[3] / "models" / "all-MiniLM-L6-v2"
    name = os.environ.get("EMBEDDING_MODEL", str(default))
    # This matcher is an optional accuracy-preserving fallback. Never turn a
    # request-time label lookup into a network download.
    try:
        return SentenceTransformer(name, device="cpu", local_files_only=True)
    except TypeError:  # compatibility with older sentence-transformers
        return SentenceTransformer(name, device="cpu")


@lru_cache(maxsize=1)
def _prototype_embeddings():
    names = tuple(FIELD_PROTOTYPES)
    vectors = _model().encode(tuple(FIELD_PROTOTYPES[name] for name in names), normalize_embeddings=True)
    return names, np.asarray(vectors)


def words_clustering(words: tuple[str, ...], tolerance: float = .65) -> dict[int, list[str]]:
    """The notebook's AgglomerativeClustering implementation."""
    embeddings = _model().encode(words, normalize_embeddings=True)
    try:
        from sklearn.cluster import AgglomerativeClustering
        try:
            clustering = AgglomerativeClustering(n_clusters=None, distance_threshold=tolerance, metric="cosine", linkage="average")
        except TypeError:
            clustering = AgglomerativeClustering(n_clusters=None, distance_threshold=tolerance, affinity="cosine", linkage="average")
        labels = clustering.fit_predict(embeddings)
        groups: dict[int, list[str]] = {}
        for word, label in zip(words, labels):
            groups.setdefault(int(label), []).append(word)
        return groups
    except Exception:
        return {index: [word] for index, word in enumerate(words)}


@lru_cache(maxsize=2048)
def semantic_field_match(label: str, threshold: float = .80) -> tuple[str | None, float]:
    """Resolve only ambiguous labels; exact aliases remain the caller's priority."""
    expanded = expand_label(label)
    prototypes = tuple(FIELD_PROTOTYPES.values())
    candidates = list(prototypes)
    try:
        clusters = words_clustering((expanded, *prototypes), tolerance=.65)
        cluster = next((values for values in clusters.values() if expanded in values), [])
        clustered = [value for value in cluster if value in prototypes]
        if clustered:
            candidates = clustered
        encoded = _model().encode((expanded, *candidates), normalize_embeddings=True)
        scores = np.asarray(encoded[0]) @ np.asarray(encoded[1:]).T
        index = int(np.argmax(scores))
        score = float(scores[index])
        field = next(name for name, prototype in FIELD_PROTOTYPES.items() if prototype == candidates[index])
        return (field if score >= threshold else None, score)
    except Exception:
        return None, 0.0
