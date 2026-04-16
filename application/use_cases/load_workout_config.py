"""
Use case for loading workout configuration from CSV file.
"""
from typing import Optional
import csv
from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int
from externalInterface.csv_workout_config_parser import CSVWorkoutConfigParser, CSVInputError
from externalInterface.simulation_csv_parser import parse_events_csv


class LoadWorkoutConfigUseCase:
    """Use case for loading workout configuration from CSV."""

    def __init__(self, workout_repository: WorkoutRepository):
        self.workout_repository = workout_repository
        self.parser = CSVWorkoutConfigParser()

    def _detect_file_type(self, csv_file_path: str) -> str:
        """
        Detect whether the CSV is an events.csv or workout config CSV.
        
        Returns:
            'events' if it's events.csv (has TYPE, TIMESTAMP, TAG headers)
            'config' if it's a workout config CSV
        """
        try:
            with open(csv_file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    return 'config'
                
                normalized_headers = [h.strip().upper() if h else "" for h in reader.fieldnames]
                
                # Check for events.csv headers
                if "TYPE" in normalized_headers and "TIMESTAMP" in normalized_headers:
                    return 'events'
                
                return 'config'
        except Exception:
            return 'config'

    def execute(self, workout_id: int, csv_file_path: str) -> dict:
        """
        Load workout configuration from CSV file.
        Supports both workout config CSV and events.csv formats.

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

        # Detect file type and parse accordingly
        file_type = self._detect_file_type(csv_file_path)
        
        if file_type == 'events':
            # Parse events.csv
            parsed_events = parse_events_csv(csv_file_path)
            return {
                'workout_id': workout_id,
                'interval_distance': 200,  # Default interval distance in meters
                'laps_per_interval': parsed_events.implicit_laps,
                'start_mode': 'GROUP'  # Events.csv uses GROUP start mode
            }
        else:
            # Parse traditional workout config CSV
            config = self.parser.parse_csv_file(csv_file_path)

            return {
                'workout_id': config.workout_id or workout_id,
                'interval_distance': config.interval_distance,
                'laps_per_interval': config.laps_per_interval,
                'start_mode': config.start_mode
            }