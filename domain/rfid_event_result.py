from dataclasses import dataclass
from typing import Optional

from domain.runnerState import RunnerState


@dataclass(frozen=True)
class RFIDEventResult:
    decision: str
    reason: str
    state: Optional[RunnerState] = None


ACCEPTED_DECISION = "accepted"
IGNORED_DECISION = "ignored"

VALID_FINISH_REASON = "valid_finish"
INVALID_TIMESTAMP_REASON = "invalid_timestamp"
UNKNOWN_TAG_REASON = "unknown_tag"
OUT_OF_ORDER_REASON = "out_of_order_timestamp"
DUPLICATE_WITHIN_WINDOW_REASON = "duplicate_within_window"
