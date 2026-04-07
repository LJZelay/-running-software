import pytest

from application.rfid_contracts import HardwareEventType
from externalInterface.scanner_event_utils import (
    build_event_envelope,
    normalize_nfc_tag_id,
    normalize_rfid_tag_id,
    parse_timestamp_ms,
)


@pytest.mark.external
class TestScannerEventUtils:
    def test_normalize_nfc_tag_id_preserves_leading_zeros(self):
        assert normalize_nfc_tag_id(" 00-ab:cd ") == "00ABCD"

    def test_normalize_rfid_tag_id_strips_leading_zeros(self):
        assert normalize_rfid_tag_id(" 00-ab:cd ") == "ABCD"
        assert normalize_rfid_tag_id("0000") == "0"

    def test_parse_timestamp_ms_from_numeric_string(self):
        assert parse_timestamp_ms("1700000000123") == 1700000000123

    def test_build_event_envelope_valid_rfid(self):
        event = build_event_envelope(
            event_type="rfid",
            raw_tag=" 00-aa:bb:cc ",
            raw_timestamp_ms="1700000000123",
            source="reader_hardware",
            reader_id="reader-1",
            ingest_time_ms=1700000001123,
        )

        assert event.event_type == HardwareEventType.RFID
        assert event.tag_id == "AABBCC"
        assert event.timestamp_ms == 1700000000123
        assert event.ingest_time_ms == 1700000001123
        assert event.source == "reader_hardware"
        assert event.reader_id == "reader-1"
        assert len(event.event_id) > 0

    def test_build_event_envelope_valid_nfc_preserves_zeros(self):
        event = build_event_envelope(
            event_type="nfc",
            raw_tag=" 00-aa:bb:cc ",
            raw_timestamp_ms="1700000000123",
            source="reader_hardware",
            ingest_time_ms=1700000001123,
        )
        assert event.event_type == HardwareEventType.NFC
        assert event.tag_id == "00AABBCC"

    def test_build_event_envelope_invalid_event_type(self):
        with pytest.raises(ValueError):
            build_event_envelope(
                event_type="gps",
                raw_tag="AABB",
                raw_timestamp_ms=123,
                source="reader_hardware",
            )

    def test_build_event_envelope_empty_source(self):
        with pytest.raises(ValueError):
            build_event_envelope(
                event_type="rfid",
                raw_tag="AABB",
                raw_timestamp_ms=123,
                source="   ",
            )

    def test_build_event_envelope_rejects_non_positive_timestamp(self):
        with pytest.raises(ValueError, match="timestamp_ms must be positive"):
            build_event_envelope(
                event_type="rfid",
                raw_tag="AABB",
                raw_timestamp_ms=0,
                source="reader_hardware",
            )

    def test_build_event_envelope_rejects_excessive_drift(self):
        with pytest.raises(ValueError, match="timestamp drift exceeds max_drift_ms"):
            build_event_envelope(
                event_type="rfid",
                raw_tag="AABB",
                raw_timestamp_ms=1700000000000,
                source="reader_hardware",
                ingest_time_ms=1700000015001,
                max_drift_ms=10_000,
            )
