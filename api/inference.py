import io
from pathlib import Path

import numpy as np
import tensorflow as tf
from django.conf import settings
from PIL import Image

MODEL_PATH = Path(settings.BASE_DIR).parent / 'asset' / 'MobileNetV2.keras'

GRADES = ['Normal', 'Doubtful', 'Mild', 'Moderate', 'Severe']
GRADE_VALUES = np.array([0, 1, 2, 3, 4], dtype=np.float32)


class KOAClassifier:
    """Wraps the trained MobileNetV2 Kellgren-Lawrence grading model.

    Input contract (asset/metrics.json): grayscale 224x224, raw float32 in
    [0, 255]. Do not normalize here - the model's internal 'prep' layer does
    the scaling.
    """

    def __init__(self, model_path=MODEL_PATH):
        self.model = tf.keras.models.load_model(model_path, compile=False)

    def preprocess(self, file_or_bytes):
        f = io.BytesIO(file_or_bytes) if isinstance(file_or_bytes, (bytes, bytearray)) else file_or_bytes
        img = Image.open(f).convert('L').resize((224, 224), Image.LANCZOS)
        return np.asarray(img, np.float32)[None, :, :, None]

    def predict(self, file_or_bytes):
        x = self.preprocess(file_or_bytes)
        probs = self.model.predict(x, verbose=0)[0]
        grade = int(np.argmax(probs))
        return {
            'grade': grade,
            'grade_label': GRADES[grade],
            'confidence': float(probs[grade]),
            'expected_grade': float(np.dot(probs, GRADE_VALUES)),
            'probabilities': probs.tolist(),
            'has_osteoarthritis': grade >= 2,
        }


_classifier = None


def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = KOAClassifier()
    return _classifier
