from datetime import datetime
from typing import Optional
from uuid import uuid4

from application.rfid_contracts import HardwareEventType, RFIDEventEnvelope


def _normalize_common(raw_tag: str) -> str:
    if raw_tag is None:
        raise ValueError("tag_id must not be None")

    normalized = raw_tag.strip().upper().replace(":", "").replace("-", "").replace(" ", "")
    if len(normalized) == 0:
        raise ValueError("tag_id must not be empty")

    return normalized


def normalize_rfid_tag_id(raw_tag: str) -> str:
    """Match reader_hardware canonical RFID behavior: strip leading zeros."""
    normalized = _normalize_common(raw_tag)
    return normalized.lstrip("0") or "0"


def normalize_nfc_tag_id(raw_tag: str) -> str:
    """Normalize NFC tags locally (uppercase + separator-free + trim)."""
    return _normalize_common(raw_tag)


def normalize_tag_id(raw_tag: str, event_type: Optional[str] = None) -> str:
    """Backwards-compatible dispatcher for normalization by event type."""
    if event_type is None:
        return normalize_nfc_tag_id(raw_tag)

    normalized_event_type = event_type.strip().upper()
    if normalized_event_type == HardwareEventType.RFID.value:
        return normalize_rfid_tag_id(raw_tag)
    if normalized_event_type == HardwareEventType.NFC.value:
        return normalize_nfc_tag_id(raw_tag)
    raise ValueError("event_type must be RFID or NFC")


def parse_timestamp_ms(raw_timestamp: object) -> int:
    if isinstance(raw_timestamp, int):
        return raw_timestamp

    if isinstance(raw_timestamp, float):
        return int(raw_timestamp)

    if isinstance(raw_timestamp, str):
        text = raw_timestamp.strip()
        if len(text) == 0:
            raise ValueError("timestamp_ms must not be empty")
        try:
            return int(float(text))
        except ValueError as exc:
            raise ValueError("timestamp_ms must be numeric") from exc

    raise ValueError("timestamp_ms must be int/float/str")


def now_epoch_ms() -> int:
    return int(datetime.now().timestamp() * 1000)


def build_event_envelope(
    event_type: str,
    raw_tag: str,
    raw_timestamp_ms: object,
    source: str,
    reader_id: Optional[str] = None,
    ingest_time_ms: Optional[int] = None,
    max_drift_ms: int = 10_000,
) -> RFIDEventEnvelope:
    normalized_event_type = event_type.strip().upper()
    if normalized_event_type not in {HardwareEventType.RFID.value, HardwareEventType.NFC.value}:
        raise ValueError("event_type must be RFID or NFC")

    if source is None or len(source.strip()) == 0:
        raise ValueError("source must not be empty")

    event_timestamp_ms = parse_timestamp_ms(raw_timestamp_ms)
    resolved_ingest_time_ms = now_epoch_ms() if ingest_time_ms is None else parse_timestamp_ms(ingest_time_ms)

    if event_timestamp_ms <= 0:
        raise ValueError("timestamp_ms must be positive")

    if resolved_ingest_time_ms <= 0:
        raise ValueError("ingest_time_ms must be positive")

    if abs(event_timestamp_ms - resolved_ingest_time_ms) > max_drift_ms:
        raise ValueError("timestamp drift exceeds max_drift_ms")

    return RFIDEventEnvelope(
        event_id=str(uuid4()),
        event_type=HardwareEventType(normalized_event_type),
        tag_id=normalize_tag_id(raw_tag, normalized_event_type),
        timestamp_ms=event_timestamp_ms,
        ingest_time_ms=resolved_ingest_time_ms,
        source=source.strip(),
        reader_id=reader_id,
    )
