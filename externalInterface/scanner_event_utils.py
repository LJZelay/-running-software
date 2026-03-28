from datetime import datetime
from typing import Optional
from uuid import uuid4

from application.rfid_contracts import HardwareEventType, RFIDEventEnvelope


def normalize_tag_id(raw_tag: str) -> str:
    """Normalize hardware tag IDs at adapter boundary without altering semantic value."""
    if raw_tag is None:
        raise ValueError("tag_id must not be None")

    normalized = raw_tag.strip().upper().replace(":", "").replace("-", "").replace(" ", "")
    if len(normalized) == 0:
        raise ValueError("tag_id must not be empty")

    return normalized


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
) -> RFIDEventEnvelope:
    normalized_event_type = event_type.strip().upper()
    if normalized_event_type not in {HardwareEventType.RFID.value, HardwareEventType.NFC.value}:
        raise ValueError("event_type must be RFID or NFC")

    if source is None or len(source.strip()) == 0:
        raise ValueError("source must not be empty")

    event_timestamp_ms = parse_timestamp_ms(raw_timestamp_ms)
    resolved_ingest_time_ms = now_epoch_ms() if ingest_time_ms is None else parse_timestamp_ms(ingest_time_ms)

    return RFIDEventEnvelope(
        event_id=str(uuid4()),
        event_type=HardwareEventType(normalized_event_type),
        tag_id=normalize_tag_id(raw_tag),
        timestamp_ms=event_timestamp_ms,
        ingest_time_ms=resolved_ingest_time_ms,
        source=source.strip(),
        reader_id=reader_id,
    )
