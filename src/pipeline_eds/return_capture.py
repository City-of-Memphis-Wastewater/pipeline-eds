# src/pipeline_eds/return_capture.py

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Union
import uuid


# ----------------------------
# Core data wrapper (optional but useful)
# ----------------------------

@dataclass
class CaptureRecord:
    """
    Standard wrapper for anything coming from an API call.
    Keeps metadata consistent across live + bounded writes.
    """
    id: str
    timestamp: str
    mode: str  # "live" | "final"
    source: str
    payload: Any
    meta: dict[str, Any]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_normalizer(response: Any) -> Any:
    """
    Default passthrough normalizer.
    Replace or extend for API-specific cleaning logic.
    """
    return response


# ----------------------------
# File IO primitives
# ----------------------------

def atomic_write_json(path: Path, data: Any) -> None:
    """
    Safely write a full JSON snapshot using atomic replace.
    """
    path = Path(path)
    tmp_path = path.with_suffix(path.suffix + ".tmp")

    tmp_path.parent.mkdir(parents=True, exist_ok=True)

    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    tmp_path.replace(path)


def append_jsonl(path: Path, record: dict) -> None:
    """
    Append a single JSON record to a .jsonl file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ----------------------------
# Capture layer (main API)
# ----------------------------

def capture_response(
    response: Any,
    *,
    source: str,
    mode: str = "final",
    normalizer: Callable[[Any], Any] = default_normalizer,
    meta: Optional[dict[str, Any]] = None,
) -> CaptureRecord:
    """
    Convert raw API response into a structured capture record.
    """
    return CaptureRecord(
        id=str(uuid.uuid4()),
        timestamp=_utc_now_iso(),
        mode=mode,
        source=source,
        payload=normalizer(response),
        meta=meta or {},
    )


# ----------------------------
# High-level save functions
# ----------------------------

def save_final_snapshot(
    response: Any,
    *,
    path: Union[str, Path],
    source: str,
    normalizer: Callable[[Any], Any] = default_normalizer,
    meta: Optional[dict[str, Any]] = None,
) -> CaptureRecord:
    """
    Write a bounded/final snapshot.
    Overwrites a single JSON file atomically.
    """
    record = capture_response(
        response,
        source=source,
        mode="final",
        normalizer=normalizer,
        meta=meta,
    )

    atomic_write_json(Path(path), asdict(record))
    return record


def save_live_event(
    response: Any,
    *,
    path: Union[str, Path],
    source: str,
    normalizer: Callable[[Any], Any] = default_normalizer,
    meta: Optional[dict[str, Any]] = None,
) -> CaptureRecord:
    """
    Write a live event as an append-only JSONL entry.
    """
    record = capture_response(
        response,
        source=source,
        mode="live",
        normalizer=normalizer,
        meta=meta,
    )

    append_jsonl(Path(path), asdict(record))
    return record


# ----------------------------
# Convenience unified API
# ----------------------------

def save_capture(
    response: Any,
    *,
    path: Union[str, Path],
    source: str,
    mode: str = "final",
    normalizer: Callable[[Any], Any] = default_normalizer,
    meta: Optional[dict[str, Any]] = None,
) -> CaptureRecord:
    """
    Unified entry point:
    - mode="final" → atomic JSON snapshot
    - mode="live"  → JSONL append
    """
    if mode == "live":
        return save_live_event(
            response,
            path=path,
            source=source,
            normalizer=normalizer,
            meta=meta,
        )

    return save_final_snapshot(
        response,
        path=path,
        source=source,
        normalizer=normalizer,
        meta=meta,
    )


# ----------------------------
# Optional helper: batch capture
# ----------------------------

def save_batch_final(
    responses: list[Any],
    *,
    path: Union[str, Path],
    source: str,
    normalizer: Callable[[Any], Any] = default_normalizer,
) -> CaptureRecord:
    """
    For bounded queries returning multiple payloads.
    Stores everything in a single final snapshot.
    """
    combined = {
        "count": len(responses),
        "items": [
            capture_response(r, source=source, mode="final", normalizer=normalizer).payload
            for r in responses
        ],
    }

    record = capture_response(
        combined,
        source=source,
        mode="final",
        normalizer=normalizer,
    )

    atomic_write_json(Path(path), asdict(record))
    return record
