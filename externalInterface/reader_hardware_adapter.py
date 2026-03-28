from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Callable, Optional

from externalInterface.scanner_adapter import ScannerAdapter, ScannerPayload


@dataclass(frozen=True)
class ReaderHardwareAdapterConfig:
    event_type: str
    source: str


class ReaderHardwareQueueAdapter(ScannerAdapter):
    """Bridge reader_hardware queue-based readers into the ScannerAdapter protocol."""

    def __init__(self, reader: object, event_queue: queue.Queue, config: ReaderHardwareAdapterConfig):
        self._reader = reader
        self._event_queue = event_queue
        self._config = config
        self._callback: Optional[Callable[[ScannerPayload], None]] = None
        self._running = False
        self._pump_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def set_event_callback(self, callback: Callable[[ScannerPayload], None]) -> None:
        self._callback = callback

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._reader.start()
        self._pump_thread = threading.Thread(target=self._pump_events, name="ReaderHardwarePump", daemon=True)
        self._pump_thread.start()

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        self._reader.stop()
        if self._pump_thread and self._pump_thread.is_alive():
            self._pump_thread.join(timeout=2.0)

    def healthcheck(self) -> bool:
        reader_running = bool(getattr(self._reader, "running", False))
        pump_running = bool(self._pump_thread and self._pump_thread.is_alive())
        return self._running and reader_running and pump_running

    def _pump_events(self) -> None:
        while not self._stop_event.is_set():
            try:
                tag_id, timestamp_ms = self._event_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if self._callback is None:
                continue

            payload = ScannerPayload(
                event_type=self._config.event_type,
                tag_id=str(tag_id),
                timestamp_ms=int(timestamp_ms),
                source=self._config.source,
            )
            self._callback(payload)


def _append_reader_hardware_sys_path(repo_root: Optional[str] = None) -> None:
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2] / "reader_hardware"
    if not root.exists():
        raise RuntimeError(f"reader_hardware not found at: {root}")

    root_str = str(root)
    if root_str not in sys.path:
        sys.path.append(root_str)

    # Ensure package-local relative imports inside reader_hardware keep working.
    for subdir in ("rfid_impinj_rest_reader", "nfc_reader", "utils"):
        candidate = root / subdir
        candidate_str = str(candidate)
        if candidate.exists() and candidate_str not in sys.path:
            sys.path.append(candidate_str)


def create_rfid_rest_adapter(scanner_address: str, repo_root: Optional[str] = None) -> ReaderHardwareQueueAdapter:
    """Create adapter around reader_hardware REST RFID reader."""
    _append_reader_hardware_sys_path(repo_root)

    from rfid_impinj_rest import ReaderRfidImpinjRest  # type: ignore

    event_q: queue.Queue = queue.Queue()
    reader = ReaderRfidImpinjRest(scanner_address, event_q)
    return ReaderHardwareQueueAdapter(
        reader=reader,
        event_queue=event_q,
        config=ReaderHardwareAdapterConfig(event_type="RFID", source="reader_hardware.rest"),
    )


def create_nfc_adapter(repo_root: Optional[str] = None) -> ReaderHardwareQueueAdapter:
    """Create adapter around reader_hardware NFC reader."""
    _append_reader_hardware_sys_path(repo_root)

    from acr122u_nfc import NFCReader  # type: ignore

    event_q: queue.Queue = queue.Queue()
    reader = NFCReader(event_q)
    return ReaderHardwareQueueAdapter(
        reader=reader,
        event_queue=event_q,
        config=ReaderHardwareAdapterConfig(event_type="NFC", source="reader_hardware.nfc"),
    )
