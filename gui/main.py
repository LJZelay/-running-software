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
from gui.coach_view import CoachView
from gui.runner_view import RunnerView


def main():
    # Setup repository and use cases
    repo = InMemoryWorkoutRepository()
    # (Optionally load some default data or allow loading via GUI)
    # We'll create a default workout if none exists
    from domain.workout import Workout
    from domain.runner import Runner
    from domain.runnerSession import RunnerSession

    # If no workout exists, create one (ID=1)
    existing = repo.get_by_id(1)
    if not existing:
        workout = Workout(workout_id=1, intervalDistance=400, lapsPerInterval=1, startMode="INDIVIDUAL")
        repo.save(workout)

    # Create use cases
    get_rest_uc = GetRestScreenUseCase(repo)
    get_running_uc = GetRunningScreenUseCase(repo)
    get_runner_analytics_uc = GetRunnerAnalyticsUseCase(repo)
    get_workout_stats_uc = GetWorkoutStatsUseCase(repo)

    # For optional controls (if we add them later)
    start_uc = StartWorkoutUseCase(repo)
    end_uc = EndWorkoutUseCase(repo)
    nfc_uc = ScanNFCUseCase(repo)
    rfid_uc = ScanRFIDUseCase(repo)
    group_start_uc = GroupStartUseCase(repo)
    add_runner_uc = AddRunnerToWorkoutUseCase(repo)

    # Launch GUI windows
    root = tk.Tk()
    coach = CoachView(
        root,
        get_rest_uc,
        get_running_uc,
        get_runner_analytics_uc,
        get_workout_stats_uc,
        workout_id=1,
        refresh_interval_ms=1000
    )
    coach.pack(fill=tk.BOTH, expand=True)

    # Optionally launch runner view (might be a separate window)
    # runner_window = tk.Toplevel(root)
    # runner = RunnerView(runner_window, get_runner_analytics_uc, get_rest_uc, runner_id=1, ...)

    root.mainloop()


if __name__ == "__main__":
    main()