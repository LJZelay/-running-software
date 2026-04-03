"""ACR122U NFC reader that listens for card insertions and emits (tag_id, timestamp_ms) tuples."""

import threading
import time
from queue import Queue
from typing import Optional

from externalInterface.scanner_event_utils import now_epoch_ms


def _load_smartcard_modules():
    from smartcard.CardMonitoring import CardMonitor, CardObserver  # type: ignore[import-not-found]
    from smartcard.Exceptions import CardConnectionException, NoCardException  # type: ignore[import-not-found]
    from smartcard.System import readers  # type: ignore[import-not-found]
    from smartcard.util import toHexString  # type: ignore[import-not-found]

    return CardMonitor, CardObserver, CardConnectionException, NoCardException, readers, toHexString


class NFCReader:
    def __init__(self, event_q: Queue):
        self.queue = event_q
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self._monitor = None
        self._observer = None

        _, _, _, _, readers, _ = _load_smartcard_modules()
        if not readers():
            raise ConnectionError("Connection to NFC Scanner failed")

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

    def _run(self):
        CardMonitor, CardObserver, CardConnectionException, NoCardException, _, toHexString = _load_smartcard_modules()

        GET_UID_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]

        # Local observer receives add/remove card events from pyscard CardMonitor.
        class _TagObserver(CardObserver):
            def __init__(self, on_tag):
                self._on_tag = on_tag

            def update(self, observable, actions):
                added, _removed = actions
                for card in added:
                    try:
                        connection = card.createConnection()
                        connection.connect()
                        response, sw1, sw2 = connection.transmit(GET_UID_APDU)
                        connection.disconnect()
                        if sw1 == 0x90 and sw2 == 0x00:
                            self._on_tag(toHexString(response))
                    except (NoCardException, CardConnectionException):
                        continue
                    except Exception:
                        continue

        def _on_tag(uid: str):
            # Adapter expects tuple payloads that the queue bridge can consume.
            self.queue.put((uid, now_epoch_ms()))

        self._observer = _TagObserver(_on_tag)
        self._monitor = CardMonitor()
        self._monitor.addObserver(self._observer)

        while self.running:
            time.sleep(0.1)

        # Ensure observer detaches cleanly when stopping the reader thread.
        if self._monitor is not None and self._observer is not None:
            self._monitor.deleteObserver(self._observer)
            self._monitor = None
            self._observer = None
