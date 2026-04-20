#!/usr/bin/env python3
"""
GUI launcher for the Interval Training Management Tool.
"""

import sys
import os
import tkinter as tk

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository
from application.use_cases.get_rest_screen import GetRestScreenUseCase
from application.use_cases.get_running_screen import GetRunningScreenUseCase
from application.use_cases.get_runner_analytics import GetRunnerAnalyticsUseCase
from application.use_cases.get_workout_stats import GetWorkoutStatsUseCase
from application.use_cases.start_workout import StartWorkoutUseCase
from application.use_cases.end_workout import EndWorkoutUseCase
from application.use_cases.scan_nfc import ScanNFCUseCase
from application.use_cases.scan_rfid import ScanRFIDUseCase
from application.use_cases.group_start import GroupStartUseCase
from application.use_cases.add_runner_to_workout import AddRunnerToWorkoutUseCase
from application.use_cases.generate_runner_report import GenerateRunnerReportUseCase
from application.use_cases.load_workout_config import LoadWorkoutConfigUseCase
from application.use_cases.load_roster import LoadRosterUseCase
from application.use_cases.edit_timestamp import EditTimestampUseCase
from externalInterface.runner_pdf_report_service import RunnerPdfReportService
from gui.coach_view import CoachView
from gui.runner_view import RunnerView


def main():
    # Setup repository and use cases
    repo = InMemoryWorkoutRepository()
    # (Optionally load some default data or allow loading via GUI)
    # We'll create a default workout if none exists
    from domain.workout import Workout
    from domain.workoutState import WorkoutState
    from domain.runner import Runner
    from domain.runnerSession import RunnerSession

    # If no workout exists, create one (ID=1) with no runners initially
    existing = repo.get_by_id(1)
    if not existing:
        workout = Workout(workout_id=1, intervalDistance=400, lapsPerInterval=1, startMode="INDIVIDUAL")
        repo.save(workout)
    else:
        workout = existing

    # Create use cases
    get_rest_uc = GetRestScreenUseCase(repo)
    get_running_uc = GetRunningScreenUseCase(repo)
    get_runner_analytics_uc = GetRunnerAnalyticsUseCase(repo)
    get_workout_stats_uc = GetWorkoutStatsUseCase(repo)

    # For optional controls
    start_uc = StartWorkoutUseCase(repo)
    end_uc = EndWorkoutUseCase(repo)
    nfc_uc = ScanNFCUseCase(repo)
    rfid_uc = ScanRFIDUseCase(repo)
    group_start_uc = GroupStartUseCase(repo)
    add_runner_uc = AddRunnerToWorkoutUseCase(repo)
    pdf_service = RunnerPdfReportService()
    generate_report_uc = GenerateRunnerReportUseCase(pdf_service)
    load_workout_config_uc = LoadWorkoutConfigUseCase(repo)
    load_roster_uc = LoadRosterUseCase(repo)
    edit_timestamp_uc = EditTimestampUseCase(repo)

    # Launch GUI windows
    root = tk.Tk()
    coach = CoachView(
        root,
        get_rest_uc,
        get_running_uc,
        get_runner_analytics_uc,
        get_workout_stats_uc,
        repo=repo,
        workout_id=1,
        start_workout_uc=start_uc,
        end_workout_uc=end_uc,
        add_runner_uc=add_runner_uc,
        nfc_uc=nfc_uc,
        rfid_uc=rfid_uc,
        generate_report_uc=generate_report_uc,
        load_workout_config_uc=load_workout_config_uc,
        load_roster_uc=load_roster_uc,
        edit_timestamp_uc=edit_timestamp_uc,
        refresh_interval_ms=1000
    )
    coach.pack(fill=tk.BOTH, expand=True)
    coach.runner_windows = []  # Track runner windows for management

    root.mainloop()


if __name__ == "__main__":
    main()