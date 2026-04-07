"""Use case for group start - activate workout and prepare selected runners via NFC."""
from typing import Optional, Tuple
from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int
from domain.runnerState import RunnerState


class GroupStartUseCase:
    """Use case for activating a workout and preparing selected runners in the group."""
    
    def __init__(self, workout_repository: WorkoutRepository):
        self.workout_repository = workout_repository
    
    def execute(self, workout_id: int, group_nfc_tags: Optional[list[str]] = None) -> Tuple[int, int, int]:
        """
        Activate workout and move selected NOT_STARTED runners to READY.
        
        Args:
            workout_id: ID of the workout
            group_nfc_tags: NFC tags that define the selected group. If omitted,
                all runners in the workout are considered selected.
        
        Returns:
            Tuple of (ready_count, active_count, resting_count)
        
        Raises:
            WorkoutNotFoundError: If workout doesn't exist
        """
        validate_positive_int(workout_id, "workout_id")
        
        # Get workout
        workout = self.workout_repository.get_by_id(workout_id)
        if not workout:
            raise WorkoutNotFoundError(f"Workout with ID {workout_id} not found")
        
        # Check if there are any runners
        if not workout.runnerSessions:
            raise ValueError("Cannot start group: No runners in workout")
        
        # Start workout if not already active
        if workout.is_not_started():
            workout.start()
        
        # Only proceed if workout is active
        if not workout.is_active():
            raise ValueError(f"Cannot start group: Workout is {workout.status.value}")
        
        selected_tags = set(group_nfc_tags) if group_nfc_tags else None

        # Group start only prepares selected runners; NFC scans begin intervals.
        ready_count = 0
        for runner_session in workout.runnerSessions:
            if runner_session.state == RunnerState.NOT_STARTED or runner_session.is_ready():
                if selected_tags is not None and runner_session.runner.nfc_tag not in selected_tags:
                    continue
                if runner_session.state == RunnerState.NOT_STARTED:
                    try:
                        runner_session.mark_ready()
                        ready_count += 1
                    except ValueError:
                        # Skip if runner cannot be prepared for any reason
                        continue
        
        # Save updated workout
        self.workout_repository.save(workout)
        
        # Get current counts
        active_count, resting_count = workout.get_runner_counts()
        
        return ready_count, active_count, resting_count
