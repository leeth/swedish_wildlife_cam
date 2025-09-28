from __future__ import annotations
from typing import List, Tuple, Optional
from pathlib import Path

from PIL import Image

from .detector import Detection


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def filter_bboxes(
    detections: List[Detection],
    img_w: int,
    img_h: int,
    conf: float,
    min_rel_area: float,
    max_rel_area: float,
    min_aspect: float,
    max_aspect: float,
    edge_margin_px: int,
    tiny_rel: float = 0.01,
) -> Tuple[List[Detection], int]:
    """
    Filter detections by confidence, relative area, aspect ratio and edge proximity.

    Returns (filtered_detections, dropped_count).
    """
    if not detections:
        return [], 0

    image_area: float = float(max(1, img_w) * max(1, img_h))

    kept: List[Detection] = []
    dropped: int = 0

    for det in detections:
        # Require bbox and confidence
        if det.bbox is None or det.confidence is None:
            dropped += 1
            continue

        if det.confidence < conf:
            dropped += 1
            continue

        x1, y1, x2, y2 = det.bbox

        # Basic bbox validity
        if x2 <= x1 or y2 <= y1:
            dropped += 1
            continue

        w = float(x2 - x1)
        h = float(y2 - y1)

        # Relative area and tiny-box check
        box_area = w * h
        rel_area = box_area / image_area if image_area > 0 else 0.0

        if rel_area < min_rel_area or rel_area > max_rel_area:
            dropped += 1
            continue

        if rel_area < tiny_rel:
            dropped += 1
            continue

        # Aspect ratio (w/h)
        aspect = w / h if h > 0 else 0.0
        if aspect < min_aspect or aspect > max_aspect:
            dropped += 1
            continue

        # Edge margin: drop boxes too close to any border
        if (
            x1 < edge_margin_px or y1 < edge_margin_px or
            (img_w - x2) < edge_margin_px or (img_h - y2) < edge_margin_px
        ):
            dropped += 1
            continue

        kept.append(det)

    return kept, dropped


def is_doubtful(
    det: Detection,
    img_w: int,
    img_h: int,
    conf_threshold: float,
    edge_margin_px: int,
    tiny_rel: float = 0.01,
    min_rel_area: float = 0.003,
    doubt_conf_margin: float = 0.05,
) -> bool:
    """
    Heuristic to mark detections for manual review before Stage-2.
    Doubt criteria:
      - confidence within [conf_threshold, conf_threshold + doubt_conf_margin)
      - box too close to image edges (within edge_margin_px)
      - very small relative area (< tiny_rel) or just above min_rel_area
    """
    if det.bbox is None or det.confidence is None:
        return True

    x1, y1, x2, y2 = det.bbox
    if x2 <= x1 or y2 <= y1 or img_w <= 0 or img_h <= 0:
        return True

    # Near-threshold confidence
    if conf_threshold <= det.confidence < (conf_threshold + doubt_conf_margin):
        return True

    # Edge proximity
    if (
        x1 < edge_margin_px or y1 < edge_margin_px or
        (img_w - x2) < edge_margin_px or (img_h - y2) < edge_margin_px
    ):
        return True

    # Relative area checks
    w = float(x2 - x1)
    h = float(y2 - y1)
    rel_area = (w * h) / float(max(1, img_w * img_h))
    if rel_area < tiny_rel or (min_rel_area <= rel_area < (min_rel_area * 1.5)):
        return True

    return False

def crop_with_padding(
    image_path: Path,
    bbox_xyxy: Tuple[float, float, float, float],
    pad_rel: float = 0.15,
    out_size: Optional[Tuple[int, int]] = None,
):
    """
    Read image, expand bbox by relative padding, clamp to image bounds, and return
    (PIL.Image, (x1, y1, x2, y2)) where bbox is integers in pixel space.
    """
    img = Image.open(image_path).convert("RGB")
    iw, ih = img.size

    x1, y1, x2, y2 = bbox_xyxy
    # Ensure numbers
    x1 = float(x1); y1 = float(y1); x2 = float(x2); y2 = float(y2)

    w = max(1.0, x2 - x1)
    h = max(1.0, y2 - y1)

    # Padding relative to bbox size
    pad_w = w * pad_rel
    pad_h = h * pad_rel

    px1 = _clamp(x1 - pad_w, 0.0, float(iw))
    py1 = _clamp(y1 - pad_h, 0.0, float(ih))
    px2 = _clamp(x2 + pad_w, 0.0, float(iw))
    py2 = _clamp(y2 + pad_h, 0.0, float(ih))

    # Convert to int box for cropping
    ix1 = int(round(px1))
    iy1 = int(round(py1))
    ix2 = int(round(px2))
    iy2 = int(round(py2))

    # Safety to avoid zero-sized crop
    if ix2 <= ix1:
        ix2 = min(iw, ix1 + 1)
    if iy2 <= iy1:
        iy2 = min(ih, iy1 + 1)

    crop = img.crop((ix1, iy1, ix2, iy2))

    if out_size is not None:
        crop = crop.resize(out_size, Image.BILINEAR)

    return crop, (ix1, iy1, ix2, iy2)


