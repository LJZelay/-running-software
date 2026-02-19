from typing import List, Tuple
from domain.workout import Workout
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from application.csvInput import CSVInputParser, CSVInputError


class CSVWorkoutImporter:
    """
    Outer-layer helper: ties CSV parsing to domain objects.
    """

    def __init__(self, parser: CSVInputParser = None):
        self.parser = parser or CSVInputParser(strict_validation=True)

    def import_roster_to_workout(
        self,
        workout: Workout,
        csv_file_path: str,
        default_rest_duration: int,
        starting_runner_id: int = 1,
    ) -> Tuple[Workout, List[RunnerSession]]:
        """
        Reads CSV -> creates Runner -> creates RunnerSession -> adds to Workout.
        """
        rows = self.parser.parse_csv_file(csv_file_path)

        ok, errors = self.parser.validate_unique_tags(rows)
        if not ok:
            raise CSVInputError("Duplicate tags found: " + "; ".join(errors))

        runners = self.parser.create_runners(rows, starting_id=starting_runner_id)
        sessions: List[RunnerSession] = []

        for r in runners:
            rs = RunnerSession(runner=r, restDuration=default_rest_duration)
            added = workout.add_runner_session(rs)
            if not added:
                raise CSVInputError("Workout already started; cannot add runner sessions")
            sessions.append(rs)

        return workout, sessions
