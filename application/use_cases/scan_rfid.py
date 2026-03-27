from uuid import uuid4

from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int, validate_non_empty_string
from application.dto.rfid_scan_result_view import RFIDScanResultView
from application.mappers import WorkoutStatusMapper
from application.rfid_contracts import RFIDDecision, RFIDReason
from domain.rfid_event_result import ACCEPTED_DECISION


class ScanRFIDUseCase: #Use case for handling the logic when an RFID tag is scanned to start a runner's activity in a workout. It validates the input, retrieves the workout, records the RFID start, saves the workout, and returns the updated workout status.
    
    def __init__(self, workout_repository: WorkoutRepository) -> None:
        self.workout_repository = workout_repository
    
    def execute(self, workout_id: int, rfid_tag_id: str, timestamp: str, use_event_time: bool = False) -> RFIDScanResultView:
        validate_positive_int(workout_id, "workout_id")
        validate_non_empty_string(rfid_tag_id, "rfid_tag_id")
        validate_non_empty_string(timestamp, "timestamp")
        
        workout = self.workout_repository.get_by_id(workout_id)
        
        if workout is None:
            raise WorkoutNotFoundError(f"Workout with id {workout_id} not found")
        
        event_timestamp = timestamp if use_event_time else None
        event_result = workout.record_rfid_event(rfid_tag_id, event_timestamp)

        if event_result.decision == ACCEPTED_DECISION:
            self.workout_repository.save(workout)
        
        status_view = WorkoutStatusMapper.from_workout(workout)
        return RFIDScanResultView(
            event_id=str(uuid4()),
            decision=RFIDDecision(event_result.decision),
            reason=RFIDReason(event_result.reason),
            workout_status=status_view,
        )
