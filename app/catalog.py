from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "catalog.json"


@lru_cache(maxsize=1)
def load_catalog() -> list[dict[str, Any]]:
    """Load the normalized catalog once per process."""
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def catalog_size() -> int:
    return len(load_catalog())
