from __future__ import annotations

from typing import TYPE_CHECKING

# from .image_loader import create_image_loader  # TODO: Implement image loader
from .logging_config import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from .detector import Detection

# Initialize logger for stages
logger = get_logger("wildlife_pipeline.stages")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def filter_bboxes(
    detections: list[Detection],
    img_w: int,
    img_h: int,
    conf: float,
    min_rel_area: float,
    max_rel_area: float,
    min_aspect: float,
    max_aspect: float,
    edge_margin_px: int,
    tiny_rel: float = 0.01,
) -> tuple[list[Detection], int]:
    """
    Filter detections by confidence, relative area, aspect ratio and edge proximity.

    Returns (filtered_detections, dropped_count).
    """
    logger.info(f"🔍 Filtering {len(detections)} detections",
                total_detections=len(detections), image_size=(img_w, img_h),
                confidence_threshold=conf, min_rel_area=min_rel_area, max_rel_area=max_rel_area,
                min_aspect=min_aspect, max_aspect=max_aspect, edge_margin=edge_margin_px)

    if not detections:
        logger.info("📭 No detections to filter")
        return [], 0

    image_area: float = float(max(1, img_w) * max(1, img_h))

    kept: list[Detection] = []
    dropped: int = 0
    dropped_reasons = {
        'confidence': 0,
        'area': 0,
        'aspect_ratio': 0,
        'edge_proximity': 0,
        'tiny_object': 0,
        'invalid_bbox': 0
    }

    for det in detections:
        # Require bbox and confidence
        if det.bbox is None or det.confidence is None:
            dropped += 1
            dropped_reasons['invalid_bbox'] += 1
            logger.debug("❌ Dropped detection: missing bbox or confidence",
                        detection=det.label, reason='invalid_bbox')
            continue

        if det.confidence < conf:
            dropped += 1
            dropped_reasons['confidence'] += 1
            logger.debug(f"❌ Dropped detection: confidence {det.confidence:.3f} < {conf}",
                        detection=det.label, confidence=det.confidence, reason='confidence')
            continue

        x1, y1, x2, y2 = det.bbox

        # Basic bbox validity
        if x2 <= x1 or y2 <= y1:
            dropped += 1
            dropped_reasons['invalid_bbox'] += 1
            logger.debug("❌ Dropped detection: invalid bbox dimensions",
                        detection=det.label, bbox=det.bbox, reason='invalid_bbox')
            continue

        w = float(x2 - x1)
        h = float(y2 - y1)

        # Relative area and tiny-box check
        box_area = w * h
        rel_area = box_area / image_area if image_area > 0 else 0.0

        if rel_area < min_rel_area or rel_area > max_rel_area:
            dropped += 1
            dropped_reasons['area'] += 1
            logger.debug(f"❌ Dropped detection: area {rel_area:.4f} not in [{min_rel_area}, {max_rel_area}]",
                        detection=det.label, rel_area=rel_area, reason='area')
            continue

        if rel_area < tiny_rel:
            dropped += 1
            dropped_reasons['tiny_object'] += 1
            logger.debug(f"❌ Dropped detection: tiny object (area: {rel_area:.4f})",
                        detection=det.label, rel_area=rel_area, reason='tiny_object')
            continue

        # Aspect ratio (w/h)
        aspect = w / h if h > 0 else 0.0
        if aspect < min_aspect or aspect > max_aspect:
            dropped += 1
            dropped_reasons['aspect_ratio'] += 1
            logger.debug(f"❌ Dropped detection: aspect ratio {aspect:.2f} not in [{min_aspect}, {max_aspect}]",
                        detection=det.label, aspect_ratio=aspect, reason='aspect_ratio')
            continue

        # Edge margin: drop boxes too close to any border
        if (
            x1 < edge_margin_px or y1 < edge_margin_px or
            (img_w - x2) < edge_margin_px or (img_h - y2) < edge_margin_px
        ):
            dropped += 1
            dropped_reasons['edge_proximity'] += 1
            logger.debug(f"❌ Dropped detection: too close to edge (margin: {edge_margin_px}px)",
                        detection=det.label, bbox=det.bbox, reason='edge_proximity')
            continue

        kept.append(det)
        logger.debug(f"✅ Kept detection: {det.label} (conf: {det.confidence:.3f}, area: {rel_area:.4f})",
                    detection=det.label, confidence=det.confidence, rel_area=rel_area)

    # Log filtering results
    logger.log_detection_stats(
        total_detections=len(detections),
        filtered_detections=len(kept),
        dropped_detections=dropped,
        dropped_reasons=dropped_reasons,
        filter_ratio=len(kept) / len(detections) if detections else 0
    )

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
    return bool(rel_area < tiny_rel or min_rel_area <= rel_area < min_rel_area * 1.5)

def crop_with_padding(
    image_path: Path,
    bbox_xyxy: tuple[float, float, float, float],
    pad_rel: float = 0.15,
    out_size: tuple[int, int] | None = None,
):
    """
    Read image, expand bbox by relative padding, clamp to image bounds, and return
    (PIL.Image, (x1, y1, x2, y2)) where bbox is integers in pixel space.
    """
    logger.debug(f"🖼️ Cropping image: {image_path.name}",
                image_path=str(image_path), bbox=bbox_xyxy, padding_ratio=pad_rel, out_size=out_size)

    # Use image loader abstraction
    from PIL import Image
    img = Image.open(image_path)
    iw, ih = img.size

    x1, y1, x2, y2 = bbox_xyxy
    # Ensure numbers
    x1 = float(x1)
    y1 = float(y1)
    x2 = float(x2)
    y2 = float(y2)

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
        logger.debug(f"🔄 Resized crop to {out_size}",
                    original_size=(ix2-ix1, iy2-iy1), new_size=out_size)

    logger.debug(f"✅ Cropped successfully: {ix2-ix1}x{iy2-iy1} pixels",
                crop_size=(ix2-ix1, iy2-iy1), final_bbox=(ix1, iy1, ix2, iy2))

    return crop, (ix1, iy1, ix2, iy2)


