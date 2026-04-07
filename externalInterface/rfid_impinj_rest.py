"""Impinj REST stream reader that emits normalized (tag_id, timestamp_ms) tuples into a queue."""

import base64
import json
import threading
from queue import Queue
from urllib.parse import urljoin

import requests

from externalInterface.scanner_event_utils import now_epoch_ms, normalize_rfid_tag_id


def _base64_to_hex(base64_string: str) -> str:
    try:
        epc_bytes = base64.b64decode(base64_string)
        return epc_bytes.hex().upper()
    except Exception:
        return base64_string


class ReaderRfidImpinjRest:
    def __init__(self, scanner_address: str, queue: Queue):
        self.thread = None
        self.running = False
        self.hostname = scanner_address
        self.event_q = queue

    def extract_rfid_data(self, raw_data):
        """Extract (tag_id, timestamp_ms) tuple from Impinj stream bytes."""
        if not raw_data:
            return None

        json_string = raw_data.decode("utf-8").strip()
        if not json_string:
            return None

        try:
            data = json.loads(json_string)
        except json.JSONDecodeError:
            return None

        tag_event = data.get("tagInventoryEvent", {})
        epc = tag_event.get("epc")
        if epc is None:
            return None

        tag_id = normalize_rfid_tag_id(_base64_to_hex(epc))
        return (tag_id, now_epoch_ms())

    def _run(self):
        try:
            # Match the expected scanner lifecycle: stop previous profile, then start inventory.
            requests.post(urljoin(self.hostname, "api/v1/profiles/stop"), verify=False)
            requests.post(
                urljoin(self.hostname, "api/v1/profiles/inventory/presets/default/start"),
                verify=False,
            )
            while self.running:
                # Stream newline-delimited JSON events from the scanner endpoint.
                response = requests.get(urljoin(self.hostname, "api/v1/data/stream"), verify=False, stream=True)
                for event_data in response.iter_lines():
                    if not self.running:
                        break
                    event_tuple = self.extract_rfid_data(event_data)
                    if event_tuple:
                        self.event_q.put(event_tuple)
        except Exception:
            # Keep adapter thread alive expectations simple: reader stops on any transport/parsing failure.
            self.running = False

    def start(self):
        if self.thread is not None and self.thread.is_alive():
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join()
