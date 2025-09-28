from __future__ import annotations
from typing import Iterator, List
from pathlib import Path

def iter_images(input_root: Path, exts: List[str]) -> Iterator[Path]:
    root = Path(input_root)
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            yield p
