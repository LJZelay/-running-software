#!/usr/bin/env python3
"""
GUI launcher for the Interval Training Management Tool.
"""

import sys
import os
import tkinter as tk

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
from externalInterface.csv_roster_parser import CSVRosterParser
from gui.coach_view import CoachView


def main():
    # Setup repository and use cases
    repo = InMemoryWorkoutRepository()

    # Create a default workout if none exists
    from domain.workout import Workout
    existing = repo.get_by_id(1)
    if not existing:
        workout = Workout(workout_id=1, intervalDistance=400, lapsPerInterval=1, startMode="INDIVIDUAL")
        repo.save(workout)

    # Initialize use cases
    get_rest_uc = GetRestScreenUseCase(repo)
    get_running_uc = GetRunningScreenUseCase(repo)
    get_runner_analytics_uc = GetRunnerAnalyticsUseCase(repo)
    get_workout_stats_uc = GetWorkoutStatsUseCase(repo)
    start_workout_uc = StartWorkoutUseCase(repo)
    end_workout_uc = EndWorkoutUseCase(repo)
    nfc_uc = ScanNFCUseCase(repo)
    rfid_uc = ScanRFIDUseCase(repo)
    group_start_uc = GroupStartUseCase(repo)
    add_runner_uc = AddRunnerToWorkoutUseCase(repo)

    # CSV parser
    csv_parser = CSVRosterParser(strict_validation=False)

    # Create main window
    root = tk.Tk()
    coach = CoachView(
        root,
        repository=repo,
        get_rest_uc=get_rest_uc,
        get_running_uc=get_running_uc,
        get_runner_analytics_uc=get_runner_analytics_uc,
        get_workout_stats_uc=get_workout_stats_uc,
        start_workout_uc=start_workout_uc,
        end_workout_uc=end_workout_uc,
        group_start_uc=group_start_uc,
        scan_nfc_uc=nfc_uc,
        scan_rfid_uc=rfid_uc,
        add_runner_uc=add_runner_uc,
        csv_parser=csv_parser,
        workout_id=1,
        refresh_interval_ms=1000
    )
    coach.pack(fill=tk.BOTH, expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()