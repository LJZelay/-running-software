import queue
import threading
import time
import types
import sys

from externalInterface.reader_hardware_adapter import (
    ReaderHardwareAdapterConfig,
    ReaderHardwareQueueAdapter,
    create_rfid_rest_adapter,
)


class FakeReader:
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False


def test_reader_hardware_queue_adapter_emits_payloads_from_queue():
    event_q: queue.Queue = queue.Queue()
    reader = FakeReader()
    adapter = ReaderHardwareQueueAdapter(
        reader=reader,
        event_queue=event_q,
        config=ReaderHardwareAdapterConfig(event_type="RFID", source="reader_hardware.rest"),
    )

    seen = []
    seen_event = threading.Event()

    def on_event(payload):
        seen.append(payload)
        seen_event.set()

    adapter.set_event_callback(on_event)
    adapter.start()
    event_q.put(("00ABCD", 1704067312000))

    assert seen_event.wait(timeout=1.0)
    assert len(seen) == 1
    assert seen[0].event_type == "RFID"
    assert seen[0].tag_id == "00ABCD"
    assert seen[0].timestamp_ms == 1704067312000
    assert seen[0].source == "reader_hardware.rest"

    assert adapter.healthcheck() is True
    adapter.stop()


def test_reader_hardware_queue_adapter_healthcheck_false_when_stopped():
    event_q: queue.Queue = queue.Queue()
    reader = FakeReader()
    adapter = ReaderHardwareQueueAdapter(
        reader=reader,
        event_queue=event_q,
        config=ReaderHardwareAdapterConfig(event_type="NFC", source="reader_hardware.nfc"),
    )

    assert adapter.healthcheck() is False
    adapter.start()
    time.sleep(0.05)
    assert adapter.healthcheck() is True
    adapter.stop()
    assert adapter.healthcheck() is False


def test_create_rfid_rest_adapter_uses_reader_hardware_module(monkeypatch, tmp_path):
    repo_root = tmp_path / "reader_hardware"
    repo_root.mkdir()
    (repo_root / "rfid_impinj_rest_reader").mkdir()
    (repo_root / "nfc_reader").mkdir()
    (repo_root / "utils").mkdir()

    fake_module = types.ModuleType("rfid_impinj_rest")

    class FakeRestReader:
        def __init__(self, scanner_address, event_q):
            self.scanner_address = scanner_address
            self.event_q = event_q
            self.running = False

        def start(self):
            self.running = True

        def stop(self):
            self.running = False

    fake_module.ReaderRfidImpinjRest = FakeRestReader
    monkeypatch.setitem(sys.modules, "rfid_impinj_rest", fake_module)

    adapter = create_rfid_rest_adapter("http://localhost:5084", repo_root=str(repo_root))
    assert adapter is not None

    adapter.start()
    assert adapter.healthcheck() is True
    adapter.stop()
