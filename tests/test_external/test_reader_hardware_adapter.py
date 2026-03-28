import queue
import threading
import time

from externalInterface.reader_hardware_adapter import (
    ReaderHardwareAdapterConfig,
    ReaderHardwareQueueAdapter,
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
