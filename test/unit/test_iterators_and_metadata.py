from __future__ import annotations
from pathlib import Path

from wildlife_pipeline.ingest import iter_images
from wildlife_pipeline.video_processor import iter_videos, VideoFrame, VideoProcessor
from wildlife_pipeline.metadata import best_timestamp


def test_iter_images(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x")
    (tmp_path / "b.JPG").write_bytes(b"x")
    (tmp_path / "c.png").write_bytes(b"x")
    (tmp_path / "ignore.txt").write_bytes(b"x")
    files = list(iter_images(tmp_path, [".jpg", ".jpeg", ".png"]))
    assert len(files) == 3


def test_iter_videos(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"x")
    (tmp_path / "b.AVI").write_bytes(b"x")
    (tmp_path / "c.mov").write_bytes(b"x")
    (tmp_path / "ignore.txt").write_bytes(b"x")
    files = list(iter_videos(tmp_path))
    assert len(files) == 3


def test_best_timestamp_fs_fallback(tmp_path):
    p = tmp_path / "file.jpg"
    p.write_bytes(b"x")
    ts = best_timestamp(p, exif={})
    # Ensure it returns a datetime
    assert hasattr(ts, "isoformat")


