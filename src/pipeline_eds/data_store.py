# src/pipeline_eds/data_store.py

from __future__ import annotations

import json

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .context import PIPELINE_APP_DIR

def get_data_dir() -> Path:
    path = PIPELINE_APP_DIR / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def atomic_write_json(
    path: Path,
    data: Any,
) -> None:
    path = Path(path)

    tmp_path = path.with_suffix(path.suffix + ".tmp")

    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    tmp_path.replace(path)


def save_json(
    data: Any,
    *,
    path: str | Path,
) -> Path:
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    atomic_write_json(path, data)

    return path


def load_json(
    path: str | Path,
) -> Any:
    path = Path(path)

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_timestamped_json(
    data: Any,
    *,
    prefix: str,
) -> Path:
    filename = (
        f"{prefix}_"
        f"{utc_timestamp()}.json"
    )

    path = get_data_dir() / filename

    atomic_write_json(path, data)

    return path


def latest_file(
    prefix: str,
) -> Path | None:
    candidates = sorted(
        get_data_dir().glob(f"{prefix}_*.json")
    )

    if not candidates:
        return None

    return candidates[-1]


def load_latest(
    prefix: str,
) -> Any:
    path = latest_file(prefix)

    if path is None:
        raise FileNotFoundError(
            f"No saved files found for prefix '{prefix}'"
        )

    return load_json(path)
