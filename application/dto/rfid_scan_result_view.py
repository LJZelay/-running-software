from dataclasses import dataclass

from application.dto.workout_status_view import WorkoutStatusView
from application.rfid_contracts import RFIDDecision, RFIDReason
from typing import Optional


@dataclass(frozen=True)
class RFIDScanResultView:
    event_id: str
    decision: RFIDDecision
    reason: RFIDReason
    workout_status: WorkoutStatusView
    runner_id: Optional[int] = None
    runner_name: Optional[str] = None

    # Backward-compatible convenience properties for existing callers.
    @property
    def workout_id(self) -> int:
        return self.workout_status.workout_id

    @property
    def workout_state(self) -> str:
        return self.workout_status.workout_state

    @property
    def active_runner_count(self) -> int:
        return self.workout_status.active_runner_count

    @property
    def resting_runner_count(self) -> int:
        return self.workout_status.resting_runner_count
