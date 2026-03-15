import sys
from datetime import datetime, timezone
from typing import Dict, List

from application.WorkoutConfig import WorkoutConfig
from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository
from application.use_cases.add_runner_to_workout import AddRunnerToWorkoutUseCase
from application.use_cases.scan_nfc import ScanNFCUseCase
from application.use_cases.scan_rfid import ScanRFIDUseCase
from application.use_cases.start_workout import StartWorkoutUseCase
from domain.runner import Runner
from domain.workout import Workout
from externalInterface.simulation_csv_parser import (
    ParsedAthlete,
    ParsedCommand,
    SimulationCSVError,
    parse_athletes_csv,
    parse_commands_csv,
)


def _epoch_ms_to_iso(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc).isoformat()


def _duration_seconds(start_iso: str, end_iso: str) -> float:
    start_dt = datetime.fromisoformat(start_iso)
    end_dt = datetime.fromisoformat(end_iso)
    return (end_dt - start_dt).total_seconds()


def _format_seconds(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _register_runners(
    athletes: List[ParsedAthlete],
    workout_id: int,
    add_runner_use_case: AddRunnerToWorkoutUseCase,
    rest_seconds: int,
) -> None:
    for index, athlete in enumerate(athletes, start=1):
        runner_name = athlete.first_name
        if athlete.last_name:
            runner_name = f"{athlete.first_name} {athlete.last_name}"

        runner = Runner(
            runner_id=index,
            name=runner_name,
            email=athlete.email,
            nfc_tag=athlete.nfc_tag,
            rfid_tag=athlete.rfid_tag,
        )
        add_runner_use_case.execute(workout_id, runner, rest_duration=rest_seconds)


def _process_commands(
    commands: List[ParsedCommand],
    workout_id: int,
    start_workout_use_case: StartWorkoutUseCase,
    scan_nfc_use_case: ScanNFCUseCase,
    scan_rfid_use_case: ScanRFIDUseCase,
) -> None:
    current_group: List[str] = []

    for command in commands:
        if command.command_type == "GROUP":
            for nfc in command.nfc_tags or []:
                if nfc not in current_group:
                    current_group.append(nfc)
            continue

        if command.command_type == "START":
            if command.timestamp_ms is None:
                continue

            start_iso = _epoch_ms_to_iso(command.timestamp_ms)
            start_workout_use_case.execute(workout_id, start_iso, use_event_time=True)

            for nfc in current_group:
                try:
                    scan_nfc_use_case.execute(workout_id, nfc, start_iso, use_event_time=True)
                except ValueError:
                    continue
            current_group.clear()
            continue

        if command.command_type == "NFC":
            if command.nfc_tag is None or command.timestamp_ms is None:
                continue
            try:
                scan_nfc_use_case.execute(
                    workout_id,
                    command.nfc_tag,
                    _epoch_ms_to_iso(command.timestamp_ms),
                    use_event_time=True,
                )
            except ValueError:
                continue
            continue

        if command.command_type == "RFID":
            if command.rfid_tag is None or command.timestamp_ms is None:
                continue
            try:
                scan_rfid_use_case.execute(
                    workout_id,
                    command.rfid_tag,
                    _epoch_ms_to_iso(command.timestamp_ms),
                    use_event_time=True,
                )
            except ValueError:
                continue


def _print_runner_summary(workout, athletes: List[ParsedAthlete]) -> None:
    athletes_by_nfc: Dict[str, ParsedAthlete] = {athlete.nfc_tag: athlete for athlete in athletes}

    for runner_session in workout.runnerSessions:
        athlete = athletes_by_nfc.get(runner_session.runner.nfc_tag)
        if athlete:
            first_name = athlete.first_name
            last_name = athlete.last_name
        else:
            name_parts = runner_session.runner.name.split(" ")
            first_name = name_parts[0] if name_parts else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        values: List[str] = [first_name, last_name]

        for index, interval in enumerate(runner_session.intervals):
            start_iso = interval.get("start")
            end_iso = interval.get("end")
            if start_iso and end_iso:
                values.append(_format_seconds(_duration_seconds(start_iso, end_iso)))

            if index < len(runner_session.rests):
                rest = runner_session.rests[index]
                rest_start = rest.get("start")
                rest_end = rest.get("end")
                if rest_start and rest_end:
                    values.append(_format_seconds(_duration_seconds(rest_start, rest_end)))

        print(", ".join(values))


def main(argv: List[str]) -> int:
    if len(argv) != 3:
        print("Usage: python simulation.py <athletes.csv> <commands.csv>")
        return 1

    athletes_csv_path = argv[1]
    commands_csv_path = argv[2]

    try:
        athletes = parse_athletes_csv(athletes_csv_path)
        commands = parse_commands_csv(commands_csv_path)
    except SimulationCSVError as error:
        print(f"Input error: {error}")
        return 1

    config = WorkoutConfig(interval_distance=400, rest_time_seconds=60, laps_per_interval=1)
    workout_id = 1

    repository = InMemoryWorkoutRepository()
    workout = Workout(
        workout_id=workout_id,
        intervalDistance=config.interval_distance,
        lapsPerInterval=config.laps_per_interval,
        startMode="GROUP",
    )
    repository.save(workout)

    add_runner_use_case = AddRunnerToWorkoutUseCase(repository)
    start_workout_use_case = StartWorkoutUseCase(repository)
    scan_nfc_use_case = ScanNFCUseCase(repository)
    scan_rfid_use_case = ScanRFIDUseCase(repository)

    _register_runners(
        athletes=athletes,
        workout_id=workout_id,
        add_runner_use_case=add_runner_use_case,
        rest_seconds=config.rest_time_seconds,
    )

    _process_commands(
        commands=commands,
        workout_id=workout_id,
        start_workout_use_case=start_workout_use_case,
        scan_nfc_use_case=scan_nfc_use_case,
        scan_rfid_use_case=scan_rfid_use_case,
    )

    updated_workout = repository.get_by_id(workout_id)
    _print_runner_summary(updated_workout, athletes)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
