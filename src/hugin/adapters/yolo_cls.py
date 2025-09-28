from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


@dataclass
class ClsResult:
    label: str
    confidence: float


class YOLOClassifier:
    def __init__(self, weights: str, conf: float = 0.5):
        from ultralytics import YOLO
        self.model = YOLO(weights)  # cls weights
        self.conf = conf
        self.names = None

    def predict_image(self, img: Image.Image) -> ClsResult:
        r = self.model.predict(img, conf=self.conf, verbose=False)[0]
        # Ultralytics cls: r.probs.top1, r.names, r.probs.top1conf
        top1 = int(r.probs.top1)
        name = r.names[top1]
        conf = float(r.probs.top1conf)
        return ClsResult(label=name, confidence=conf)


