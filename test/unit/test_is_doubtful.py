from __future__ import annotations

from wildlife_pipeline.detector import Detection
from wildlife_pipeline.stages import is_doubtful


def test_is_doubtful_near_threshold():
    det = Detection(label="moose", confidence=0.31, bbox=[10, 10, 50, 50])
    assert is_doubtful(det, 100, 100, conf_threshold=0.30, edge_margin_px=12) is True


def test_is_doubtful_edge_proximity():
    det = Detection(label="moose", confidence=0.9, bbox=[2, 2, 20, 20])
    assert is_doubtful(det, 100, 100, conf_threshold=0.30, edge_margin_px=12) is True


def test_is_doubtful_small_area():
    det = Detection(label="moose", confidence=0.9, bbox=[10, 10, 12, 12])
    assert is_doubtful(det, 100, 100, conf_threshold=0.30, edge_margin_px=12) is True


def test_is_doubtful_confident_and_center():
    det = Detection(label="moose", confidence=0.9, bbox=[20, 20, 80, 80])
    assert is_doubtful(det, 100, 100, conf_threshold=0.30, edge_margin_px=12) is False


