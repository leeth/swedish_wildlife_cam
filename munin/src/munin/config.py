from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

@dataclass
class PipelineConfig:
    input_root: Path
    output_path: Path
    model_path: Optional[str] = None  # e.g., "yolov8n.pt" or custom wildlife model
    conf_thres: float = 0.35
    iou_thres: float = 0.5
    write_format: str = "csv"  # or "parquet"
    exts: List[str] = None

    def __post_init__(self):
        if self.exts is None:
            self.exts = [".jpg", ".jpeg", ".png", ".bmp", ".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"]
