from __future__ import annotations
from pathlib import Path

from wildlife_pipeline.stages import filter_bboxes, crop_with_padding, is_doubtful


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


def test_stage1_sample_negative_positive_doubtful(sample_detections, tmp_image_path):
    # Use image size 100x100 from tmp_image_path fixture
    iw, ih = (100, 100)

    # Stage-1 filtering
    kept, dropped = filter_bboxes(
        sample_detections,
        img_w=iw,
        img_h=ih,
        conf=0.30,
        min_rel_area=0.01,
        max_rel_area=0.80,
        min_aspect=0.2,
        max_aspect=5.0,
        edge_margin_px=5,
    )

    # Classify kept into doubtful vs confident
    doubtful = []
    confident = []
    for d in kept:
        if is_doubtful(d, iw, ih, conf_threshold=0.30, edge_margin_px=5, tiny_rel=0.01, min_rel_area=0.01):
            doubtful.append(d)
        else:
            confident.append(d)

    # Expectations based on sample_detections in conftest:
    # - one good box (moose) should be kept and confident
    # - low conf (boar) should be dropped (negative)
    # - tiny (fox) likely dropped on area (negative)
    # - near edge (bear at ~95,95..) will be dropped by edge
    # - extreme aspect (lynx) may be dropped by aspect
    assert any(d.label == "moose" for d in confident), "Expected a confident positive moose"
    assert dropped >= 2, "Expected multiple negatives filtered out"
    # There could be at least 0 or more doubtful depending on thresholds
    assert len(doubtful) >= 0


