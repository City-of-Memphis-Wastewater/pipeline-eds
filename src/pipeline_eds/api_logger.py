# src/pipeline_eds/api_logger.py

from __future__ import annotations

import json
import os
import uuid

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .context import PIPELINE_APP_DIR

API_LOG_ENV_VAR = "PIPELINE_EDS_CAPTURE_API"


class ApiLogKind(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"


REDACT_KEYS = {
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "password",
    "sessionid",
    "session_id",
    "api_key",
    "apikey",
    "secret",
}


def capture_enabled() -> bool:
    value = os.environ.get(API_LOG_ENV_VAR, "")
    return value.lower() in {"1", "true", "yes", "on"}


def get_api_log_dir() -> Path:
    path = PIPELINE_APP_DIR / "api_logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sanitize_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            key: (
                "***REDACTED***"
                if key.lower() in REDACT_KEYS
                else sanitize_json(value)
            )
            for key, value in obj.items()
        }

    if isinstance(obj, list):
        return [sanitize_json(item) for item in obj]

    if isinstance(obj, tuple):
        return [sanitize_json(item) for item in obj]

    return obj


def atomic_write_json(path: Path, data: Any) -> None:
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


@dataclass(slots=True)
class ApiTransaction:
    service: str
    id: str
    timestamp: str

    @classmethod
    def create(cls, service: str) -> "ApiTransaction":
        return cls(
            service=service,
            id=uuid.uuid4().hex[:8],
            timestamp=utc_timestamp(),
        )


def build_log_path(
    transaction: ApiTransaction,
    kind: ApiLogKind,
) -> Path:
    filename = (
        f"{transaction.service}_"
        f"{transaction.id}_"
        f"{kind.value}.json"
    )

    return get_api_log_dir() / filename


def write_payload(
    transaction: ApiTransaction,
    *,
    kind: ApiLogKind,
    payload: Any,
) -> Path:
    path = build_log_path(transaction, kind)

    record = {
        "transaction_id": transaction.id,
        "service": transaction.service,
        "timestamp": transaction.timestamp,
        "kind": kind.value,
        "payload": sanitize_json(payload),
    }

    atomic_write_json(path, record)

    return path


def log_request(
    transaction: ApiTransaction,
    payload: Any,
) -> Path:
    if not capture_enabled():
        return Path()

    return write_payload(
        transaction,
        kind=ApiLogKind.REQUEST,
        payload=payload,
    )


def log_response(
    transaction: ApiTransaction,
    payload: Any,
) -> Path:
    if not capture_enabled():
        return Path()

    return write_payload(
        transaction,
        kind=ApiLogKind.RESPONSE,
        payload=payload,
    )


def log_request_and_response(
    *,
    service: str,
    request: Any,
    response: Any,
) -> str:
    if not capture_enabled():
        return ""

    txn = ApiTransaction.create(service)

    log_request(txn, request)
    log_response(txn, response)

    return txn.id
