from types import SimpleNamespace

from application.rfid_contracts import HardwareEventType, RFIDEventEnvelope
from controller import cli as cli_module


def test_worker_dispatch_routes_nfc_events_to_scan_nfc_use_case():
    cli = cli_module.IntervalTrainingCLI()
    calls = []

    class _StubNFCUseCase:
        def execute(self, workout_id, nfc_tag_id, timestamp, use_event_time=False):
            calls.append((workout_id, nfc_tag_id, timestamp, use_event_time))
            return SimpleNamespace(active_runner_count=1, resting_runner_count=0)

    cli.scan_nfc_uc = _StubNFCUseCase()

    event = RFIDEventEnvelope(
        event_id="evt-nfc-1",
        event_type=HardwareEventType.NFC,
        tag_id="NFC001",
        timestamp_ms=1704067205000,
        ingest_time_ms=1704067205001,
        source="reader_hardware.nfc",
    )

    result = cli._process_rfid_worker_event(event)

    assert len(calls) == 1
    assert calls[0][0] == cli.workout_id
    assert calls[0][1] == "NFC001"
    assert calls[0][3] is True
    assert result["event_type"] == "NFC"
    assert result["active_runner_count"] == 1
    assert result["resting_runner_count"] == 0

    cli.cmd_exit([])


def test_optional_nfc_adapter_initializes_when_enabled(monkeypatch):
    fake_adapter = SimpleNamespace(
        callback=None,
        started=False,
        stopped=False,
    )

    def set_event_callback(callback):
        fake_adapter.callback = callback

    def start():
        fake_adapter.started = True

    def stop():
        fake_adapter.stopped = True

    fake_adapter.set_event_callback = set_event_callback
    fake_adapter.start = start
    fake_adapter.stop = stop

    monkeypatch.setattr(cli_module, "create_nfc_adapter", lambda: fake_adapter)
    monkeypatch.setenv("FEATURE2_ENABLE_NFC", "1")

    cli = cli_module.IntervalTrainingCLI()

    assert cli.hardware_nfc_adapter is fake_adapter
    assert fake_adapter.started is True
    assert callable(fake_adapter.callback)

    cli.cmd_exit([])
    assert fake_adapter.stopped is True


def test_cli_runs_without_hardware_configuration(monkeypatch):
    monkeypatch.delenv("FEATURE2_ENABLE_NFC", raising=False)
    monkeypatch.delenv("FEATURE2_NFC_ENABLED", raising=False)
    monkeypatch.delenv("FEATURE2_RFID_REST_URL", raising=False)

    cli = cli_module.IntervalTrainingCLI()

    assert cli.hardware_nfc_adapter is None
    assert cli.hardware_rfid_adapter is None
    assert cli.rfid_worker_service is not None

    cli.cmd_exit([])