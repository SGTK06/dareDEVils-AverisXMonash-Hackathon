"""Lazy Sentence Transformer embedding service."""
class SentenceEmbeddingService:
    def __init__(self, model_name: str, batch_size: int = 32):
        self.model_name, self.batch_size, self._model = model_name, batch_size, None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str]):
        return self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
