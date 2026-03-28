from dataclasses import dataclass
from typing import Callable, Optional, Protocol


@dataclass(frozen=True)
class ScannerPayload:
    event_type: str
    tag_id: str
    timestamp_ms: int
    source: str
    reader_id: Optional[str] = None


class ScannerAdapter(Protocol):
    """Transport-only adapter boundary for scanner integrations."""

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def healthcheck(self) -> bool:
        ...

    def set_event_callback(self, callback: Callable[[ScannerPayload], None]) -> None:
        ...
