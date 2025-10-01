from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Any
from pathlib import Path

from ..common.core.base import BaseDetector
from ..common.types import DetectionResult
from ..common.exceptions import ProcessingError, ValidationError
from ..common.utils.logging_utils import get_logger, ProcessingTimer

if TYPE_CHECKING:
    pass


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: list[float] | None = None  # [x1,y1,x2,y2] in pixels

    def to_detection_result(self) -> DetectionResult:
        """Convert to DetectionResult."""
        return DetectionResult(
            bbox=tuple(self.bbox) if self.bbox else (0, 0, 0, 0),
            confidence=self.confidence,
            class_name=self.label,
            class_id=0,  # Default class ID
            metadata={"original_detection": True}
        )

class YOLODetector(BaseDetector):
    """
    Ultralytics YOLO detector adapter.
    Works with object detection models (.pt). For wildlife,
    plug in your custom model path trained on deer/boar/elk/etc.
    """
    def __init__(self, model_path: str, conf: float = 0.35, iou: float = 0.5, **kwargs):
        super().__init__(model_path=model_path, **kwargs)
        self.conf = conf
        self.iou = iou
        self.logger = get_logger(self.__class__.__name__)

        # Validate parameters
        if not 0 <= conf <= 1:
            raise ValidationError("Confidence threshold must be between 0 and 1")
        if not 0 <= iou <= 1:
            raise ValidationError("IoU threshold must be between 0 and 1")

    def load_model(self) -> None:
        """Load the YOLO model."""
        try:
            from ultralytics import YOLO  # lazy import
        except Exception as e:
            raise ProcessingError(
                "Ultralytics not installed. Please `pip install ultralytics`."
            ) from e

        try:
            self.logger.info(f"Loading YOLO model from {self.model_path}")
            self.model = YOLO(str(self.model_path))
            self.logger.info("YOLO model loaded successfully")
        except Exception as e:
            raise ProcessingError(f"Failed to load YOLO model: {e}") from e

    def detect(self, image_data: Any) -> List[DetectionResult]:
        """Detect objects in the image.

        Args:
            image_data: Image data (path, numpy array, or PIL Image)

        Returns:
            List of detection results
        """
        if self.model is None:
            raise ProcessingError("Model not loaded. Call load_model() first.")

        # Convert input to path if needed
        if isinstance(image_data, (str, Path)):
            image_path = Path(image_data)
        else:
            # For other types, we'll need to handle them differently
            raise ValidationError(f"Unsupported image data type: {type(image_data)}")

        if not image_path.exists():
            raise ValidationError(f"Image file not found: {image_path}")

        try:
            with ProcessingTimer(self.logger, f"YOLO detection on {image_path}"):
                results = self.model.predict(
                    source=str(image_path),
                    conf=self.conf,
                    iou=self.iou,
                    imgsz=1280,
                    verbose=False
                )

                detections = self._process_results(results)
                self.logger.info(f"YOLO detected {len(detections)} objects")
                return detections

        except Exception as e:
            raise ProcessingError(f"YOLO detection failed: {e}") from e

    def _process_results(self, results) -> List[DetectionResult]:
        """Process YOLO results into DetectionResult objects."""
        detections = []

        if not results:
            return detections

        result = results[0]
        names = result.names  # class id -> label

        if result.boxes is None:
            return detections

        for box in result.boxes:
            try:
                cls_id = int(box.cls.item())
                label = names.get(cls_id, str(cls_id))
                conf = float(box.conf.item())
                xyxy = [float(v) for v in box.xyxy[0].tolist()]

                detection = DetectionResult(
                    bbox=tuple(xyxy),
                    confidence=conf,
                    class_name=label,
                    class_id=cls_id,
                    metadata={"detector": "YOLO", "model_path": str(self.model_path)}
                )
                detections.append(detection)

            except Exception as e:
                self.logger.warning(f"Failed to process detection: {e}")
                continue

        return detections

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
