"""
Use case for loading workout configuration from CSV file.
"""
from typing import Optional
from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int
from externalInterface.csv_workout_config_parser import CSVWorkoutConfigParser, CSVInputError


class LoadWorkoutConfigUseCase:
    """Use case for loading workout configuration from CSV."""

    def __init__(self, workout_repository: WorkoutRepository):
        self.workout_repository = workout_repository
        self.parser = CSVWorkoutConfigParser()

    def execute(self, workout_id: int, csv_file_path: str) -> dict:
        """
        Load workout configuration from CSV file.

        Args:
            workout_id: ID of the workout to configure
            csv_file_path: Path to the CSV configuration file

        Returns:
            Dictionary with configuration data

        Raises:
            WorkoutNotFoundError: If workout doesn't exist
            CSVInputError: If CSV parsing fails
        """
        validate_positive_int(workout_id, "workout_id")

        # Verify workout exists
        workout = self.workout_repository.get_by_id(workout_id)
        if not workout:
            raise WorkoutNotFoundError(f"Workout with ID {workout_id} not found")

        # Parse CSV
        config = self.parser.parse_csv_file(csv_file_path)

        return {
            'workout_id': config.workout_id or workout_id,
            'interval_distance': config.interval_distance,
            'laps_per_interval': config.laps_per_interval,
            'start_mode': config.start_mode
        }