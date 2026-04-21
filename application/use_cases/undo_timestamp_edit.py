from typing import Any, Dict, Optional

from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int


class UndoLastTimestampEditUseCase:
    """
    Coach/admin use case: revert the most recent manual timestamp edit for a
    runner. Intended for fat-finger recovery after EditTimestampUseCase.
    """

    def __init__(self, workout_repository: WorkoutRepository) -> None:
        self.workout_repository = workout_repository

    def execute(
        self,
        workout_id: int,
        runner_id: int,
    ) -> Optional[Dict[str, Any]]:
        validate_positive_int(workout_id, "workout_id")
        validate_positive_int(runner_id, "runner_id")

        workout = self.workout_repository.get_by_id(workout_id)
        if workout is None:
            raise WorkoutNotFoundError(f"Workout with id {workout_id} not found")

        runner_session = next(
            (rs for rs in workout.runnerSessions if rs.runner.id == runner_id),
            None,
        )
        if runner_session is None:
            raise ValueError(
                f"Runner with id {runner_id} not found in workout {workout_id}"
            )

        result = runner_session.undo_last_edit()
        if result is not None:
            self.workout_repository.save(workout)
        return result
