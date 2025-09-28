from __future__ import annotations
from pathlib import Path

from wildlife_pipeline.stages import filter_bboxes, crop_with_padding


def test_filter_bboxes_basic(sample_detections):
    kept, dropped = filter_bboxes(
        sample_detections,
        img_w=100,
        img_h=100,
        conf=0.3,
        min_rel_area=0.01,
        max_rel_area=0.8,
        min_aspect=0.2,
        max_aspect=5.0,
        edge_margin_px=5,
    )

    # Expect at least the first good box kept
    assert any(d.label == "moose" for d in kept)
    # Some detections should be dropped for various reasons
    assert dropped >= 1


def test_crop_with_padding(tmp_image_path):
    crop, box = crop_with_padding(tmp_image_path, (10, 10, 60, 60), pad_rel=0.1)
    x1, y1, x2, y2 = box
    assert x1 < 10 and y1 < 10  # padded outward
    assert x2 > 60 and y2 > 60  # padded outward
    assert crop.width == (x2 - x1) and crop.height == (y2 - y1)


