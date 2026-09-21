"""Load and run the persisted Random Forest classifier."""
import joblib

class RandomForestMailModel:
    def __init__(self, path):
        self.path, self._classifier = path, None

    @property
    def classifier(self):
        if self._classifier is None:
            if not self.path.exists():
                raise FileNotFoundError(f"trained classifier not found: {self.path}")
            self._classifier = joblib.load(self.path)
        return self._classifier

    def predict(self, vector):
        return self._result(self.classifier.predict_proba(vector)[0])

    def predict_many(self, vectors):
        probabilities = self.classifier.predict_proba(vectors)
        return [self._result(row) for row in probabilities]

    def _result(self, probabilities):
        index = probabilities.argmax()
        return (str(self.classifier.classes_[index]), float(probabilities[index]),
                {str(label): float(score) for label, score in zip(self.classifier.classes_, probabilities)})
