"""Lazy Sentence Transformer embedding service."""
class SentenceEmbeddingService:
    def __init__(self, model_name: str):
        self.model_name, self._model = model_name, None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str]):
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
