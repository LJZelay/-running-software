from datetime import datetime
import logging
from typing import List, Optional, Any, Dict, Union
from domain.runner import Runner
from domain.rfid_event_result import (
    ACCEPTED_DECISION,
    DUPLICATE_WITHIN_WINDOW_REASON,
    IGNORED_DECISION,
    INVALID_TIMESTAMP_REASON,
    OUT_OF_ORDER_REASON,
    RFIDEventResult,
    VALID_FINISH_REASON,
)
from domain.runnerState import RunnerState


logger = logging.getLogger(__name__)


class RunnerSession:
    """
    Domain Entity: RunnerSession

    Stores dynamic state of a runner during a workout session:
    - runner identity
    - restDuration (per-runner)
    - current state (RunnerState)
    - interval timestamps
    - rest timestamps

    Core rules:
    - cannot start if already running
    - cannot start if resting (unless rest expired -> READY)
    - rest expires after restDuration, then state becomes READY
    - interval finishes when laps_per_interval is reached, then rest starts immediately
    """

    def __init__(
        self,
        runner: Runner,
        restDuration: int,
        state: Optional[Union[RunnerState, str]] = None,
        intervals: Optional[List[Dict[str, Any]]] = None,
        rests: Optional[List[Dict[str, Any]]] = None,
        lastAcceptedRfidEpochMs: Optional[int] = None,
        lastAcceptedNfcEpochMs: Optional[int] = None,
    ):
        self.runner = runner
        self.restDuration = restDuration

        # Convert incoming state (string or enum) into RunnerState
        if state is None:
            self.state: RunnerState = RunnerState.NOT_STARTED
        elif isinstance(state, RunnerState):
            self.state = state
        else:
            # Expect strings like "NOT_STARTED", "READY", "RUNNING", "RESTING"
            self.state = RunnerState(state)

        self.intervals = [] if intervals is None else intervals
        self.rests = [] if rests is None else rests
        self.lastAcceptedRfidEpochMs = lastAcceptedRfidEpochMs
        self.lastAcceptedNfcEpochMs = lastAcceptedNfcEpochMs

        # History of manual timestamp edits for undo. Each entry is:
        # {"kind", "index", "field", "lap_index", "previous"}. Not
        # persisted in to_dict/from_dict; process-lifetime only.
        self._edit_history: List[Dict[str, Any]] = []

    # ---------------------------
    # Domain Behavior
    # ---------------------------

    def mark_ready(self) -> None:
        """Move a runner from NOT_STARTED to READY after group start activation."""
        if self.state != RunnerState.NOT_STARTED:
            raise ValueError("Runner cannot be marked ready from current state")
        self.state = RunnerState.READY

    def start_interval(self, timestamp: Optional[str] = None) -> None:
        # Start interval when NFC is scanned.

        if self.state == RunnerState.RUNNING:
            raise ValueError("Runner is already running")

        interval_start = timestamp if timestamp is not None else datetime.now().isoformat()

        # If runner was resting, close that rest at this NFC scan time.
        if self.state == RunnerState.RESTING:
            currentRest = self.rests[-1]
            if currentRest["end"] is None:
                currentRest["end"] = interval_start

        intervalNumber = len(self.intervals) + 1
        self.intervals.append({
            "intervalNumber": intervalNumber,
            "start": interval_start,
            "laps": [],
            "end": None
        })
        self.state = RunnerState.RUNNING

    def process_nfc_start(self, timestamp: Optional[str] = None, debounce_ms: int = 200) -> bool:
        """Apply NFC acceptance rules before starting an interval."""
        resolved = self._resolve_iso_and_epoch(timestamp)
        if resolved is None:
            logger.info(
                "event=nfc_start decision=ignored reason=invalid_timestamp runner_id=%s nfc_tag=%s",
                self.runner.id,
                self.runner.nfc_tag,
            )
            return False

        start_iso, start_epoch_ms = resolved

        if self.lastAcceptedNfcEpochMs is not None:
            if start_epoch_ms < self.lastAcceptedNfcEpochMs:
                logger.info(
                    "event=nfc_start decision=ignored reason=out_of_order_timestamp runner_id=%s nfc_tag=%s",
                    self.runner.id,
                    self.runner.nfc_tag,
                )
                return False

            if (start_epoch_ms - self.lastAcceptedNfcEpochMs) < debounce_ms:
                logger.info(
                    "event=nfc_start decision=ignored reason=duplicate_within_window runner_id=%s nfc_tag=%s",
                    self.runner.id,
                    self.runner.nfc_tag,
                )
                return False

        self.start_interval(start_iso)
        self.lastAcceptedNfcEpochMs = start_epoch_ms
        logger.info(
            "event=nfc_start decision=accepted reason=valid_start runner_id=%s nfc_tag=%s",
            self.runner.id,
            self.runner.nfc_tag,
        )
        return True

    def record_lap(self, timestamp: Optional[str] = None) -> None:
        """
        Record an RFID detection (a lap completion) while running.
        """
        if self.state != RunnerState.RUNNING:
            raise ValueError("Cannot record lap unless runner is running")
        currentInterval = self.intervals[-1]
        lap_time = timestamp if timestamp is not None else datetime.now().isoformat()
        currentInterval["laps"].append(lap_time)

    def should_finish_interval(self, lapsPerInterval: int) -> bool:
        """
        Check if current interval is complete based on number of laps.
        """
        if self.state != RunnerState.RUNNING:
            return False
        currentInterval = self.intervals[-1]
        return len(currentInterval["laps"]) >= lapsPerInterval

    def record_lap_and_update_state(self, lapsPerInterval: int, timestamp: Optional[str] = None) -> RunnerState:
        """
        Convenience method so application layer doesn't need to orchestrate finish logic.
        """
        self.record_lap(timestamp)
        if self.should_finish_interval(lapsPerInterval):
            self.finish_interval(timestamp)
        return self.state

    def process_rfid_read(
        self,
        lapsPerInterval: int,
        timestamp: Optional[str] = None,
        debounce_ms: int = 200,
    ) -> RFIDEventResult:
        """Apply RFID read acceptance rules before mutating lap/rest state."""
        if self.state != RunnerState.RUNNING:
            raise ValueError("Cannot record lap unless runner is running")

        resolved = self._resolve_iso_and_epoch(timestamp)
        if resolved is None:
            return RFIDEventResult(decision=IGNORED_DECISION, reason=INVALID_TIMESTAMP_REASON, state=self.state)

        lap_iso, lap_epoch_ms = resolved

        if self.lastAcceptedRfidEpochMs is not None:
            if lap_epoch_ms < self.lastAcceptedRfidEpochMs:
                return RFIDEventResult(decision=IGNORED_DECISION, reason=OUT_OF_ORDER_REASON, state=self.state)

            if (lap_epoch_ms - self.lastAcceptedRfidEpochMs) < debounce_ms:
                return RFIDEventResult(
                    decision=IGNORED_DECISION,
                    reason=DUPLICATE_WITHIN_WINDOW_REASON,
                    state=self.state,
                )

        self.record_lap(lap_iso)
        self.lastAcceptedRfidEpochMs = lap_epoch_ms

        if self.should_finish_interval(lapsPerInterval):
            self.finish_interval(lap_iso)

        return RFIDEventResult(decision=ACCEPTED_DECISION, reason=VALID_FINISH_REASON, state=self.state)

    @staticmethod
    def _resolve_iso_and_epoch(timestamp: Optional[str]) -> Optional[tuple[str, int]]:
        if timestamp is None:
            now_iso = datetime.now().isoformat()
            now_epoch_ms = int(datetime.fromisoformat(now_iso).timestamp() * 1000)
            return now_iso, now_epoch_ms

        try:
            parsed = datetime.fromisoformat(timestamp)
        except ValueError:
            return None

        return timestamp, int(parsed.timestamp() * 1000)

    def finish_interval(self, timestamp: Optional[str] = None) -> None:
        """
        Finish current running interval and start rest.
        """
        if self.state != RunnerState.RUNNING:
            raise ValueError("Runner is not running")

        now_iso = timestamp if timestamp is not None else datetime.now().isoformat()

        currentInterval = self.intervals[-1]
        currentInterval["end"] = now_iso

        self.rests.append({
            "start": now_iso,
            "restDuration": self.restDuration,
            "end": None
        })
        self.state = RunnerState.RESTING

    def check_if_ready(self, now: Optional[str] = None) -> None:
        """
        Check if runner is ready to start a new interval (rest period over).
        """
        if self.state != RunnerState.RESTING:
            return

        currentRest = self.rests[-1]
        startTime = datetime.fromisoformat(currentRest["start"])
        now_dt = datetime.fromisoformat(now) if now is not None else datetime.now()
        elapsed = (now_dt - startTime).total_seconds()

        if elapsed >= currentRest["restDuration"]:
            if currentRest["end"] is None:
                currentRest["end"] = now_dt.isoformat()
            self.state = RunnerState.READY

    # UI concern, might remove later
    def get_remaining_rest_seconds(self, now: Optional[str] = None) -> int:
        """
        Remaining rest seconds
        """
        if self.state != RunnerState.RESTING:
            return 0

        currentRest = self.rests[-1]
        startTime = datetime.fromisoformat(currentRest["start"])
        now_dt = datetime.fromisoformat(now) if now is not None else datetime.now()
        elapsed = (now_dt - startTime).total_seconds()

        remaining = int(currentRest["restDuration"] - elapsed)
        return max(0, remaining)
    
    def is_ready(self) -> bool:
        """
        Returns True if runner is ready to start next interval.
        """
        self.check_if_ready()
        return self.state == RunnerState.READY

    # ---------------------------
    # Manual correction (coach/admin)
    # ---------------------------

    def edit_timestamp(
        self,
        kind: str,
        index: int,
        field: str,
        new_timestamp: str,
        lap_index: Optional[int] = None,
    ) -> Optional[str]:
        """
        Coach/admin-only: manually overwrite a stored timestamp that the
        hardware recorded incorrectly.

        Arguments:
            kind: "interval" or "rest"
            index: 1-based interval number (kind="interval") or 0-based
                rest list index (kind="rest")
            field: "start" | "end" | "lap" (for intervals);
                "start" | "end" (for rests)
            new_timestamp: ISO 8601 timestamp string
            lap_index: 0-based lap index, required when kind="interval" and
                field="lap"

        Returns the previous timestamp value (may be None if unset).
        Raises ValueError on invalid arguments.
        """
        try:
            datetime.fromisoformat(new_timestamp)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid ISO 8601 timestamp: {new_timestamp!r}")

        if kind == "interval":
            if field not in ("start", "end", "lap"):
                raise ValueError(f"Invalid interval field: {field!r}")
            if not isinstance(index, int) or index < 1 or index > len(self.intervals):
                raise ValueError(f"Interval number {index} out of range")
            interval = self.intervals[index - 1]
            if field == "lap":
                laps = interval.get("laps", [])
                if (
                    not isinstance(lap_index, int)
                    or lap_index < 0
                    or lap_index >= len(laps)
                ):
                    raise ValueError(f"Lap index {lap_index} out of range")
                self._validate_logical_ordering(
                    kind, index, field, new_timestamp, lap_index
                )
                previous = laps[lap_index]
                laps[lap_index] = new_timestamp
                self._edit_history.append({
                    "kind": kind,
                    "index": index,
                    "field": field,
                    "lap_index": lap_index,
                    "previous": previous,
                })
                return previous
            self._validate_logical_ordering(
                kind, index, field, new_timestamp, lap_index
            )
            previous = interval.get(field)
            interval[field] = new_timestamp
            self._edit_history.append({
                "kind": kind,
                "index": index,
                "field": field,
                "lap_index": None,
                "previous": previous,
            })
            return previous

        if kind == "rest":
            if field not in ("start", "end"):
                raise ValueError(f"Invalid rest field: {field!r}")
            if not isinstance(index, int) or index < 0 or index >= len(self.rests):
                raise ValueError(f"Rest index {index} out of range")
            self._validate_logical_ordering(
                kind, index, field, new_timestamp, lap_index
            )
            rest = self.rests[index]
            previous = rest.get(field)
            rest[field] = new_timestamp
            self._edit_history.append({
                "kind": kind,
                "index": index,
                "field": field,
                "lap_index": None,
                "previous": previous,
            })
            return previous

        raise ValueError(f"Invalid kind: {kind!r}")

    def _validate_logical_ordering(
        self,
        kind: str,
        index: int,
        field: str,
        new_timestamp: str,
        lap_index: "Optional[int]",
    ) -> None:
        """
        Ensure the replacement timestamp stays consistent with the neighbors
        stored in the same interval or rest. Rules:

        - interval: start <= lap[0] <= lap[1] <= ... <= lap[n-1] <= end
        - rest:     start <= end

        Only neighbors that already have a value participate in the check, so
        correcting an earlier field before a later one still works.
        """
        new_dt = datetime.fromisoformat(new_timestamp)

        def _parse(value):
            if not value:
                return None
            try:
                return datetime.fromisoformat(value)
            except (TypeError, ValueError):
                return None

        if kind == "interval":
            interval = self.intervals[index - 1]
            start_dt = _parse(interval.get("start"))
            end_dt = _parse(interval.get("end"))
            laps = interval.get("laps", [])

            if field == "start":
                first_lap_dt = _parse(laps[0]) if laps else None
                upper = first_lap_dt if first_lap_dt is not None else end_dt
                if upper is not None and new_dt > upper:
                    raise ValueError(
                        "Interval start must be at or before the first lap/end"
                    )
                return

            if field == "end":
                last_lap_dt = _parse(laps[-1]) if laps else None
                lower = last_lap_dt if last_lap_dt is not None else start_dt
                if lower is not None and new_dt < lower:
                    raise ValueError(
                        "Interval end must be at or after the last lap/start"
                    )
                return

            if field == "lap":
                prev_bound = (
                    _parse(laps[lap_index - 1]) if lap_index > 0 else start_dt
                )
                next_bound = (
                    _parse(laps[lap_index + 1])
                    if lap_index + 1 < len(laps)
                    else end_dt
                )
                if prev_bound is not None and new_dt < prev_bound:
                    raise ValueError(
                        "Lap timestamp must be at or after the previous lap/start"
                    )
                if next_bound is not None and new_dt > next_bound:
                    raise ValueError(
                        "Lap timestamp must be at or before the next lap/end"
                    )
                return

        if kind == "rest":
            rest = self.rests[index]
            start_dt = _parse(rest.get("start"))
            end_dt = _parse(rest.get("end"))

            if field == "start":
                if end_dt is not None and new_dt > end_dt:
                    raise ValueError("Rest start must be at or before rest end")
                return

            if field == "end":
                if start_dt is not None and new_dt < start_dt:
                    raise ValueError("Rest end must be at or after rest start")
                return

    def undo_last_edit(self):
        """
        Revert the most recent manual timestamp edit for this runner.

        Returns a dict describing what was undone (keys: kind, index, field,
        lap_index, reverted_from, reverted_to) or None if there is nothing
        to undo.

        The restored value was valid at the time it was captured, so this
        bypasses logical-ordering validation. It also does not push a new
        entry onto the history (single-direction undo only).
        """
        if not self._edit_history:
            return None

        last = self._edit_history.pop()
        kind = last["kind"]
        index = last["index"]
        field = last["field"]
        lap_index = last.get("lap_index")
        previous = last["previous"]

        if kind == "interval":
            interval = self.intervals[index - 1]
            if field == "lap":
                current = interval["laps"][lap_index]
                interval["laps"][lap_index] = previous
            else:
                current = interval.get(field)
                interval[field] = previous
        elif kind == "rest":
            rest = self.rests[index]
            current = rest.get(field)
            rest[field] = previous
        else:
            self._edit_history.append(last)
            return None

        return {
            "kind": kind,
            "index": index,
            "field": field,
            "lap_index": lap_index,
            "reverted_from": current,
            "reverted_to": previous,
        }

    # ---------------------------
    # Persistence helpers
    # ---------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runner": self.runner.to_dict(),
            "restDuration": self.restDuration,
            "state": self.state.value, 
            "intervals": self.intervals,
            "rests": self.rests,
            "lastAcceptedRfidEpochMs": self.lastAcceptedRfidEpochMs,
            "lastAcceptedNfcEpochMs": self.lastAcceptedNfcEpochMs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunnerSession":
        return cls(
            runner=Runner.from_dict(data["runner"]),
            restDuration=data["restDuration"],
            state=data.get("state"),
            intervals=data.get("intervals"),
            rests=data.get("rests"),
            lastAcceptedRfidEpochMs=data.get("lastAcceptedRfidEpochMs"),
            lastAcceptedNfcEpochMs=data.get("lastAcceptedNfcEpochMs"),
        )