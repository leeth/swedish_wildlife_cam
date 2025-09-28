from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: list[float] | None = None  # [x1,y1,x2,y2] in pixels

class BaseDetector:
    def predict(self, image_path: Path) -> list[Detection]:
        raise NotImplementedError

class YOLODetector(BaseDetector):
    """
    Ultralytics YOLO detector adapter.
    Works with object detection models (.pt). For wildlife,
    plug in your custom model path trained on deer/boar/elk/etc.
    """
    def __init__(self, model_path: str, conf: float = 0.35, iou: float = 0.5):
        try:
            from ultralytics import YOLO  # lazy import
        except Exception as e:
            raise RuntimeError(
                "Ultralytics not installed. Please `pip install ultralytics`."
            ) from e
        self.model = YOLO(model_path)
        self.conf = conf
        self.iou = iou

    def predict(self, image_path: Path) -> list[Detection]:
        results = self.model.predict(
            source=str(image_path),
            conf=self.conf,
            iou=self.iou,
            imgsz=1280,
            verbose=False
        )
        dets: list[Detection] = []
        if not results:
            return dets
        r = results[0]
        names = r.names  # class id -> label
        if r.boxes is None:
            return dets
        for b in r.boxes:
            cls_id = int(b.cls.item())
            label = names.get(cls_id, str(cls_id))
            conf = float(b.conf.item())
            xyxy = [float(v) for v in b.xyxy[0].tolist()]
            dets.append(Detection(label=label, confidence=conf, bbox=xyxy))
        return dets
