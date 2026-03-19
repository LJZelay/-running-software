from typing import List, Tuple
from domain.workout import Workout
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from externalInterface.csv_roster_parser import CSVRosterParser, RosterData, CSVInputError


class CSVWorkoutImporter:
    """
    Orchestrates CSV parsing and domain object creation.
    Uses CSVRosterParser for format-specific parsing.
    """

    def __init__(self, parser: CSVRosterParser = None):
        self.parser = parser or CSVRosterParser(strict_validation=True)

    def import_roster_to_workout(
        self,
        workout: Workout,
        csv_file_path: str,
        default_rest_duration: int,
        starting_runner_id: int = 1,
    ) -> Tuple[Workout, List[RunnerSession]]:
        """
        Reads CSV -> parses to RosterData -> creates Runner -> creates RunnerSession -> adds to Workout.
        """
        roster_data = self.parser.parse_csv_file(csv_file_path)

        ok, errors = self.parser.validate_unique_tags(roster_data)
        if not ok:
            raise CSVInputError("Duplicate tags found: " + "; ".join(errors))

        runners = self._create_runners_from_roster(roster_data, starting_runner_id)
        sessions: List[RunnerSession] = []

        for r in runners:
            rs = RunnerSession(runner=r, restDuration=default_rest_duration)
            added = workout.add_runner_session(rs)
            if not added:
                raise CSVInputError("Workout already started; cannot add runner sessions")
            sessions.append(rs)

        return workout, sessions

    def _create_runners_from_roster(
        self,
        roster_data: List[RosterData],
        starting_id: int = 1,
    ) -> List[Runner]:
        """
        Create Runner objects from RosterData.
        """
        runners: List[Runner] = []
        for i, data in enumerate(roster_data):
            runners.append(
                Runner(
                    runner_id=starting_id + i,
                    name=data.name,
                    email=data.email or "",
                    nfc_tag=data.nfc_id,
                    rfid_tag=data.rfid_id,
                )
            )
        return runners
