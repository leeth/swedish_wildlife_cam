from __future__ import annotations
import json
from typing import Any

def to_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)
