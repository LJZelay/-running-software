"""
Use case for loading athlete roster from CSV file.
"""
from typing import List
from application.repositories.workout_repository import WorkoutRepository
from application.csvWorkoutImporter import CSVWorkoutImporter
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int
from domain.runner import Runner


class LoadRosterUseCase:
    """Use case for loading athlete roster from CSV."""

    def __init__(self, workout_repository: WorkoutRepository):
        self.workout_repository = workout_repository
        self.importer = CSVWorkoutImporter()

    def execute(self, workout_id: int, csv_file_path: str, default_rest_duration: int = 60) -> List[Runner]:
        """
        Load athlete roster from CSV file and add to workout.

        Args:
            workout_id: ID of the workout to add runners to
            csv_file_path: Path to the CSV roster file
            default_rest_duration: Default rest duration in seconds

        Returns:
            List of Runner objects that were added

        Raises:
            WorkoutNotFoundError: If workout doesn't exist
        """
        validate_positive_int(workout_id, "workout_id")

        workout = self.workout_repository.get_by_id(workout_id)
        if not workout:
            raise WorkoutNotFoundError(f"Workout with ID {workout_id} not found")

        # Import roster using the application layer importer
        workout, sessions = self.importer.import_roster_to_workout(
            workout=workout,
            csv_file_path=csv_file_path,
            default_rest_duration=default_rest_duration,
            starting_runner_id=len(workout.runnerSessions) + 1
        )

        # Save the updated workout
        self.workout_repository.save(workout)

        # Return the runners that were added
        return [session.runner for session in sessions]