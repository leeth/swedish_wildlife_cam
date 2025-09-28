from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone

from wildlife_pipeline.run_pipeline import row_from_detections
from wildlife_pipeline.detector import Detection
from wildlife_pipeline.video_processor import VideoProcessor, VideoFrame


def test_row_from_detections(tmp_path):
    img_path = tmp_path / "img.jpg"
    img_path.write_bytes(b"fake")
    ts = datetime.now(tz=timezone.utc)
    dets = [
        Detection(label="moose", confidence=0.9, bbox=[1, 2, 3, 4]),
        Detection(label="boar", confidence=0.6, bbox=[5, 6, 7, 8]),
    ]
    row = row_from_detections(img_path, "camera_A", ts, dets)
    assert row["image_path"].endswith("img.jpg")
    assert row["camera_id"] == "camera_A"
    assert row["observation_any"] is True
    assert row["top_label"] == "moose"
    assert row["top_confidence"] == 0.9


def test_video_summarize():
    class DummyDetector:
        def predict(self, image_path: Path):
            return []

    vp = VideoProcessor(detector=DummyDetector(), frame_interval=30, max_frames=5)
    frames = [
        VideoFrame(frame_number=0, timestamp=0.0, image_path=None, detections=[]),
        VideoFrame(frame_number=30, timestamp=1.0, image_path=None, detections=[Detection(label="moose", confidence=0.8, bbox=[0,0,10,10])]),
    ]
    summary = vp.summarize_video_detections(frames)
    assert summary["total_frames"] == 2
    assert summary["frames_with_detections"] == 1
    assert summary["total_detections"] == 1
    assert summary["species_detected"]["moose"] == 1


