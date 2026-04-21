"""Queue-to-callback bridge adapters that convert hardware reader tuples into ScannerPayload events."""

from __future__ import annotations

import os
import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from externalInterface.acr122u_nfc import NFCReader
from externalInterface.rfid_impinj_rest import ReaderRfidImpinjRest
from externalInterface.scanner_event_utils import now_epoch_ms, normalize_nfc_tag_id
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
        # Pump raw reader tuples into the app-facing payload callback.
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


class SimulatedNFCReader:
    """Small NFC simulator for local GUI testing without physical hardware."""

    def __init__(self, event_q: queue.Queue, tags: Optional[list[str]] = None, interval_seconds: float = 6.0):
        self.queue = event_q
        self.tags = tags or ["NFC002", "NFC003", "NFC004", "NFC005", "NFC006"]
        self.interval_seconds = interval_seconds
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self._next_index = 0

    def start(self) -> None:
        if self.thread is not None and self.thread.is_alive():
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, name="SimulatedNFCReader", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=2.0)

    def _run(self) -> None:
        while self.running:
            if not self.tags:
                time.sleep(self.interval_seconds)
                continue

            tag_id = self.tags[self._next_index % len(self.tags)]
            self._next_index += 1
            self.queue.put((tag_id, now_epoch_ms()))
            time.sleep(self.interval_seconds)


def create_rfid_rest_adapter(scanner_address: str) -> ReaderHardwareQueueAdapter:
    """Create a bridge adapter backed by the local Impinj REST RFID reader."""

    event_q: queue.Queue = queue.Queue()
    reader = ReaderRfidImpinjRest(scanner_address, event_q)
    return ReaderHardwareQueueAdapter(
        reader=reader,
        event_queue=event_q,
        config=ReaderHardwareAdapterConfig(event_type="RFID", source="reader_hardware.rest"),
    )


def create_nfc_adapter(tags: Optional[list[str]] = None) -> ReaderHardwareQueueAdapter:
    """Create a bridge adapter backed by NFC hardware or a lightweight simulator."""

    event_q: queue.Queue = queue.Queue()
    simulate_nfc = os.getenv("NFC_SIMULATOR", "1").lower() not in {"0", "false", "no"}

    if simulate_nfc:
        configured_tags = [
            tag.strip()
            for tag in os.getenv("NFC_SIM_TAGS", "NFC002,NFC003,NFC004,NFC005,NFC006").split(",")
            if tag.strip()
        ]
        if tags:
            configured_tags = [normalize_nfc_tag_id(tag) for tag in tags if str(tag).strip()]
        interval_seconds = float(os.getenv("NFC_SIM_INTERVAL", "6.0"))
        reader = SimulatedNFCReader(event_q, tags=configured_tags, interval_seconds=interval_seconds)
    else:
        reader = NFCReader(event_q)
    return ReaderHardwareQueueAdapter(
        reader=reader,
        event_queue=event_q,
        config=ReaderHardwareAdapterConfig(
            event_type="NFC",
            source="reader_hardware.nfc.simulated" if simulate_nfc else "reader_hardware.nfc",
        ),
    )
