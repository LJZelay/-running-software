from typing import Optional

from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int, validate_non_empty_string


class EditTimestampUseCase:
    """
    Coach/admin use case: manually correct a stored interval or rest
    timestamp that was misinputted by the hardware.
    """

    def __init__(self, workout_repository: WorkoutRepository) -> None:
        self.workout_repository = workout_repository

    def execute(
        self,
        workout_id: int,
        runner_id: int,
        kind: str,
        index: int,
        field: str,
        new_timestamp: str,
        lap_index: Optional[int] = None,
    ) -> Optional[str]:
        validate_positive_int(workout_id, "workout_id")
        validate_positive_int(runner_id, "runner_id")
        validate_non_empty_string(kind, "kind")
        validate_non_empty_string(field, "field")
        validate_non_empty_string(new_timestamp, "new_timestamp")

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

        previous = runner_session.edit_timestamp(
            kind=kind,
            index=index,
            field=field,
            new_timestamp=new_timestamp,
            lap_index=lap_index,
        )
        self.workout_repository.save(workout)
        return previous
