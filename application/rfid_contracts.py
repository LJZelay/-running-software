from dataclasses import dataclass
from enum import Enum
from typing import Optional


class HardwareEventType(str, Enum):
    RFID = "RFID"
    NFC = "NFC"


class RFIDDecision(str, Enum):
    ACCEPTED = "accepted"
    IGNORED = "ignored"


class RFIDReason(str, Enum):
    VALID_FINISH = "valid_finish"
    INVALID_TIMESTAMP = "invalid_timestamp"
    INVALID_TIMESTAMP_DRIFT = "invalid_timestamp_drift"
    UNKNOWN_TAG = "unknown_tag"
    DUPLICATE_EVENT_ID = "duplicate_event_id"
    OUT_OF_ORDER_TIMESTAMP = "out_of_order_timestamp"
    DUPLICATE_WITHIN_WINDOW = "duplicate_within_window"


DEFAULT_RFID_DEBOUNCE_MS = 200
DEFAULT_RFID_MAX_DRIFT_MS = 10_000
DEFAULT_RFID_QUEUE_SIZE = 500
DEFAULT_RFID_EVENT_ID_CACHE_SIZE = 1_000


@dataclass(frozen=True)
class RFIDRuntimeConfig:
    debounce_ms: int = DEFAULT_RFID_DEBOUNCE_MS
    max_drift_ms: int = DEFAULT_RFID_MAX_DRIFT_MS
    queue_size: int = DEFAULT_RFID_QUEUE_SIZE
    event_id_cache_size: int = DEFAULT_RFID_EVENT_ID_CACHE_SIZE


@dataclass(frozen=True)
class RFIDEventEnvelope:
    event_id: str
    event_type: HardwareEventType
    tag_id: str
    timestamp_ms: int
    ingest_time_ms: int
    source: str
    reader_id: Optional[str] = None
