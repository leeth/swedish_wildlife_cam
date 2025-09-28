from __future__ import annotations
from unittest.mock import MagicMock
from PIL import Image

from wildlife_pipeline.adapters.yolo_cls import YOLOClassifier


def test_yolo_classifier_predict_image_monkeypatch(monkeypatch):
    # Create a tiny image
    img = Image.new("RGB", (8, 8), color=(0, 0, 0))

    # Stub model
    class DummyProbs:
        top1 = 0
        top1conf = 0.77

    class DummyResult:
        probs = DummyProbs()
        names = {0: "moose"}

    dummy_model = MagicMock()
    dummy_model.predict.return_value = [DummyResult()]

    # Monkeypatch YOLOClassifier to avoid loading real weights
    clf = YOLOClassifier.__new__(YOLOClassifier)
    clf.model = dummy_model
    clf.conf = 0.5

    res = clf.predict_image(img)
    assert res.label == "moose"
    assert 0.5 <= res.confidence <= 1.0


