from __future__ import annotations
from typing import List
from pathlib import Path
import tempfile

import pytest
from PIL import Image

from wildlife_pipeline.detector import Detection


@pytest.fixture()
def tmp_image_path() -> Path:
    tmpdir = Path(tempfile.gettempdir())
    path = tmpdir / "unit_test_image_100x100.jpg"
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    img.save(path, format="JPEG", quality=90)
    return path


@pytest.fixture()
def sample_detections() -> List[Detection]:
    return [
        Detection(label="moose", confidence=0.9, bbox=[10, 10, 60, 60]),  # good box
        Detection(label="boar", confidence=0.2, bbox=[5, 5, 15, 15]),     # low conf
        Detection(label="fox", confidence=0.8, bbox=[0, 0, 5, 5]),        # tiny
        Detection(label="bear", confidence=0.7, bbox=[95, 95, 105, 105]), # partly outside
        Detection(label="lynx", confidence=0.6, bbox=[20, 20, 22, 60]),   # extreme aspect
    ]


