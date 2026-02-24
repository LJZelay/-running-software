#!/usr/bin/env python3
"""
Command Line Interface for Interval Training Software - Feature 1
Assumes default workout configuration: 400m intervals (1 lap), 60 seconds rest time

Menu Options:
1. Load athletes from CSV
2. Add athlete to group (by NFC tag)
3. Trigger group start
4. Send RFID tag detected event
5. Send NFC tag scanned event
6. Get list of resting athletes
7. Get list of running athletes
8. Terminate application
"""

import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Domain imports
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.workout import Workout

# Application layer imports
from application.csvInput import CSVWorkoutImporter, CSVInputParser, CSVInputError
from application.use_cases.add_runner_to_workout import AddRunnerToWorkoutUseCase
from application.use_cases.group_start import GroupStartUseCase
from application.use_cases.get_rest_screen import GetRestScreenUseCase
from application.use_cases.get_running_screen import GetRunningScreenUseCase

# Repository
from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository

# DTOs
from application.dto.runner_rest_view import RunnerRestView
from application.dto.runner_running_view import RunnerRunningView
from application.dto.workout_status_view import WorkoutStatusView

# Exceptions
from application.exceptions import WorkoutNotFoundError, InvalidApplicationRequestError


class IntervalTrainingCLI:
    """
    Command Line Interface for Interval Training Software.
    Assumes default workout: 400m intervals, 60 seconds rest time, 1 lap per interval.
    """
    
    # Default workout configuration
    DEFAULT_WORKOUT_ID = 1
    DEFAULT_INTERVAL_DISTANCE = 400
    DEFAULT_LAPS_PER_INTERVAL = 1  # 1 lap = 400m
    DEFAULT_REST_DURATION = 60
    DEFAULT_START_MODE = "INDIVIDUAL"
    
    def __init__(self):
        """Initialize CLI with default workout and use cases."""
        # Repository
        self.repository = InMemoryWorkoutRepository()
        
        # Initialize use cases
        self.add_runner_use_case = AddRunnerToWorkoutUseCase(self.repository)
        self.group_start_use_case = GroupStartUseCase(self.repository)
        self.get_rest_screen_use_case = GetRestScreenUseCase(self.repository)
        self.get_running_screen_use_case = GetRunningScreenUseCase(self.repository)
        
        # CSV utilities
        self.csv_importer = CSVWorkoutImporter()
        self.csv_parser = CSVInputParser(strict_validation=False)
        
        # Current workout
        self.workout = None
        self._create_default_workout()
        
        # Menu mapping
        self.menu_options = {
            '1': self.load_athletes_from_csv,
            '2': self.add_athlete_to_group,
            '3': self.trigger_group_start,
            '4': self.send_rfid_event,
            '5': self.send_nfc_event,
            '6': self.get_resting_athletes,
            '7': self.get_running_athletes,
            '8': self.terminate_application,
            'help': self.show_help,
            'status': self.show_workout_status
        }
    
    def _create_default_workout(self):
        """Create default workout with 400m intervals, 60s rest."""
        try:
            self.workout = Workout(
                workout_id=self.DEFAULT_WORKOUT_ID,
                intervalDistance=self.DEFAULT_INTERVAL_DISTANCE,
                lapsPerInterval=self.DEFAULT_LAPS_PER_INTERVAL,
                startMode=self.DEFAULT_START_MODE,
                status="NOT_STARTED"
            )
            self.repository.save(self.workout)
            print(f"\n✓ Created default workout (ID: {self.DEFAULT_WORKOUT_ID})")
            print(f"  Configuration: {self.DEFAULT_INTERVAL_DISTANCE}m intervals")
            print(f"  Rest time: {self.DEFAULT_REST_DURATION}s per interval")
            print(f"  Laps per interval: {self.DEFAULT_LAPS_PER_INTERVAL}")
        except Exception as e:
            print(f"✗ Failed to create default workout: {e}")
            sys.exit(1)
    
    def run(self):
        """Main CLI loop."""
        self._show_welcome()
        self.show_help()
        
        while True:
            try:
                command = input("\n❯ ").strip()
                
                if not command:
                    continue
                
                # Parse command and arguments
                parts = command.split()
                menu_option = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                
                # Handle exit
                if menu_option in ['8', 'exit', 'quit', 'q']:
                    self.terminate_application(args)
                    break
                
                # Execute command
                if menu_option in self.menu_options:
                    self.menu_options[menu_option](args)
                else:
                    print(f"  Unknown option: {menu_option}")
                    print("  Type 'help' to see available commands")
                    
            except KeyboardInterrupt:
                print("\n\n  Use option 8 to exit")
            except Exception as e:
                print(f"  Error: {e}")
    
    def _show_welcome(self):
        """Display welcome message."""
        print("\n" + "=" * 60)
        print("   INTERVAL TRAINING SOFTWARE - FEATURE 1")
        print("=" * 60)
        print(f"   Default: {self.DEFAULT_INTERVAL_DISTANCE}m | {self.DEFAULT_REST_DURATION}s rest")
        print("=" * 60)
    
    def show_help(self, args: List[str] = None):
        """Display help menu."""
        print("\n  AVAILABLE COMMANDS:")
        print("  " + "-" * 56)
        print("   1 <filepath>    - Load athletes from CSV file")
        print("   2 <nfc_tag>     - Add athlete to group (by NFC tag)")
        print("   3              - Trigger group start (all added athletes)")
        print("   4 <rfid_tag>    - Send RFID tag detected event (finish lap)")
        print("   5 <nfc_tag>     - Send NFC tag scanned event (start interval)")
        print("   6              - Get list of currently resting athletes")
        print("   7              - Get list of currently running athletes")
        print("   8              - Terminate application")
        print("  " + "-" * 56)
        print("   status         - Show current workout status")
        print("   help           - Show this help message")
        print("\n  EXAMPLES:")
        print("   1 data/athletes.csv")
        print("   2 NFC001")
        print("   4 RFID001")
        print("   5 NFC002")
        print("=" * 60)
    
    # ========== OPTION 1: Load athletes from CSV ==========
    
    def load_athletes_from_csv(self, args: List[str]):
        """
        Load athletes from CSV file.
        Usage: 1 <filepath>
        """
        if len(args) < 1:
            print("  Error: Missing file path")
            print("  Usage: 1 <filepath>")
            return
        
        file_path = args[0]
        
        if not os.path.exists(file_path):
            print(f"  Error: File not found: {file_path}")
            return
        
        try:
            # Parse CSV and create runners
            csv_data = self.csv_parser.parse_csv_file(file_path)
            runners = self.csv_parser.create_runners_from_csv(csv_data)
            
            # Create RunnerSessions for each runner with default rest duration
            added_count = 0
            for runner in runners:
                try:
                    # Check if runner already exists in workout
                    existing = self.workout._find_runner_session_by_nfc(runner.nfc_tag)
                    if existing:
                        print(f"  Warning: Runner {runner.name} already in workout, skipping")
                        continue
                    
                    # Create runner session with default rest duration
                    runner_session = RunnerSession(
                        runner=runner,
                        restDuration=self.DEFAULT_REST_DURATION,
                        state="NOT_STARTED"
                    )
                    self.workout.add_runner_session(runner_session)
                    added_count += 1
                    
                except ValueError as e:
                    print(f"  Warning: Could not add {runner.name}: {e}")
            
            # Save updated workout
            self.repository.save(self.workout)
            
            print(f"\n  ✓ Loaded {added_count} athletes from {file_path}")
            print(f"  Total athletes in workout: {len(self.workout.runnerSessions)}")
            
            # Show first few imported athletes
            if added_count > 0:
                print("\n  Imported athletes:")
                for rs in self.workout.runnerSessions[-added_count:][:3]:
                    print(f"    - {rs.runner.name} (NFC: {rs.runner.nfc_tag}, RFID: {rs.runner.rfid_tag})")
                if added_count > 3:
                    print(f"    ... and {added_count - 3} more")
                    
        except CSVInputError as e:
            print(f"  Error loading CSV: {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")
    
    # ========== OPTION 2: Add athlete to group (by NFC tag) ==========
    
    def add_athlete_to_group(self, args: List[str]):
        """
        Add athlete to group by NFC tag.
        Usage: 2 <nfc_tag>
        """
        if len(args) < 1:
            print("  Error: Missing NFC tag")
            print("  Usage: 2 <nfc_tag>")
            return
        
        nfc_tag = args[0]
        
        try:
            # Find runner in existing runner sessions
            runner_session = self.workout._find_runner_session_by_nfc(nfc_tag)
            
            if not runner_session:
                print(f"  Error: No athlete found with NFC tag: {nfc_tag}")
                print("  Tip: Load athletes from CSV first (option 1)")
                return
            
            # Check if athlete is already in group (they are if they have a runner session)
            print(f"  ✓ Athlete {runner_session.runner.name} is in the group")
            print(f"    State: {runner_session.state}")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # ========== OPTION 3: Trigger group start ==========
    
    def trigger_group_start(self, args: List[str]):
        """
        Start all athletes that have been added to the group.
        Usage: 3
        """
        if not self.workout.runnerSessions:
            print("  Error: No athletes in group")
            print("  Tip: Load athletes from CSV first (option 1)")
            return
        
        try:
            # Start workout if not already active
            if self.workout.status == "NOT_STARTED":
                self.workout.start()
                print("  ✓ Workout started")
            
            # Start all READY runners
            started_count = 0
            for rs in self.workout.runnerSessions:
                if rs.state in ["NOT_STARTED", "READY"]:
                    try:
                        rs.start_interval()
                        started_count += 1
                    except ValueError as e:
                        print(f"  Warning: Could not start {rs.runner.name}: {e}")
            
            # Save changes
            self.repository.save(self.workout)
            
            active, resting = self.workout.get_runner_counts()
            print(f"\n  ✓ Group start triggered")
            print(f"    Started: {started_count} athletes")
            print(f"    Active: {active}")
            print(f"    Resting: {resting}")
            
        except Exception as e:
            print(f"  Error starting group: {e}")
    
    # ========== OPTION 4: Send RFID tag detected event ==========
    
    def send_rfid_event(self, args: List[str]):
        """
        Send RFID tag detected event (runner finishes lap/interval).
        Usage: 4 <rfid_tag>
        """
        if len(args) < 1:
            print("  Error: Missing RFID tag")
            print("  Usage: 4 <rfid_tag>")
            return
        
        rfid_tag = args[0]
        
        try:
            # Check if workout is active
            if self.workout.status != "ACTIVE":
                print("  Error: Workout is not active")
                print("  Tip: Trigger group start first (option 3)")
                return
            
            # Find runner by RFID
            rs = self.workout._find_runner_session_by_rfid(rfid_tag)
            if not rs:
                print(f"  Error: No athlete found with RFID tag: {rfid_tag}")
                return
            
            # Record lap
            rs.record_lap()
            
            # Check if interval should finish
            if rs.should_finish_interval(self.workout.lapsPerInterval):
                rs.finish_interval()
                print(f"  ✓ {rs.runner.name} completed interval {len(rs.intervals)}")
                print(f"    State: {rs.state}, Rest: {rs.get_remaining_restDuration()}s remaining")
            else:
                laps_completed = len(rs.intervals[-1]["laps"]) if rs.intervals else 0
                print(f"  ✓ {rs.runner.name} completed lap {laps_completed}/{self.workout.lapsPerInterval}")
            
            # Save changes
            self.repository.save(self.workout)
            
            # Show updated counts
            active, resting = self.workout.get_runner_counts()
            print(f"    Active: {active}, Resting: {resting}")
            
        except ValueError as e:
            print(f"  Error processing RFID event: {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")
    
    # ========== OPTION 5: Send NFC tag scanned event ==========
    
    def send_nfc_event(self, args: List[str]):
        """
        Send NFC tag scanned event (runner starts interval).
        Usage: 5 <nfc_tag>
        """
        if len(args) < 1:
            print("  Error: Missing NFC tag")
            print("  Usage: 5 <nfc_tag>")
            return
        
        nfc_tag = args[0]
        
        try:
            # Check if workout is active
            if self.workout.status != "ACTIVE":
                print("  Error: Workout is not active")
                print("  Tip: Trigger group start first (option 3)")
                return
            
            # Find runner by NFC
            rs = self.workout._find_runner_session_by_nfc(nfc_tag)
            if not rs:
                print(f"  Error: No athlete found with NFC tag: {nfc_tag}")
                return
            
            # Check if runner is ready
            rs.check_if_ready()
            
            # Start interval
            rs.start_interval()
            
            print(f"  ✓ {rs.runner.name} started interval {len(rs.intervals)}")
            print(f"    State: {rs.state}")
            
            # Save changes
            self.repository.save(self.workout)
            
            # Show updated counts
            active, resting = self.workout.get_runner_counts()
            print(f"    Active: {active}, Resting: {resting}")
            
        except ValueError as e:
            print(f"  Error processing NFC scan: {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")
    
    # ========== OPTION 6: Get list of resting athletes ==========
    
    def get_resting_athletes(self, args: List[str]):
        """
        Get and print list of currently resting athletes.
        Usage: 6
        """
        try:
            # Update rest status for all runners
            for rs in self.workout.runnerSessions:
                rs.check_if_ready()
            
            rest_data = self.workout.get_rest_screen()
            
            if not rest_data:
                print("\n  No athletes currently resting.")
                return
            
            print("\n  " + "=" * 56)
            print("  RESTING ATHLETES")
            print("  " + "=" * 56)
            print(f"  {'Name':<20} {'Rest Remaining':<15} {'Interval':<10}")
            print("  " + "-" * 56)
            
            for data in rest_data:
                remaining = data["remaining_seconds"]
                mins = remaining // 60
                secs = remaining % 60
                time_str = f"{mins:02d}:{secs:02d}"
                
                # Find interval number for this runner
                rs = self.workout._find_runner_session_by_nfc(
                    next((rs for rs in self.workout.runnerSessions if rs.runner.id == data["runner_id"]), None)
                )
                interval_num = len(rs.intervals) if rs else 0
                
                print(f"  {data['runner_name']:<20} {time_str:<15} {interval_num:<10}")
            
            print("  " + "=" * 56)
            print(f"  Total resting: {len(rest_data)}")
            
        except Exception as e:
            print(f"  Error getting rest screen: {e}")
    
    # ========== OPTION 7: Get list of running athletes ==========
    
    def get_running_athletes(self, args: List[str]):
        """
        Get and print list of currently running athletes.
        Usage: 7
        """
        try:
            running_sessions = [rs for rs in self.workout.runnerSessions if rs.state == "RUNNING"]
            
            if not running_sessions:
                print("\n  No athletes currently running.")
                return
            
            print("\n  " + "=" * 56)
            print("  RUNNING ATHLETES")
            print("  " + "=" * 56)
            print(f"  {'Name':<20} {'Current Interval':<15} {'Laps':<15}")
            print("  " + "-" * 56)
            
            for rs in running_sessions:
                interval_num = len(rs.intervals)
                laps_completed = len(rs.intervals[-1]["laps"]) if rs.intervals else 0
                progress = f"{laps_completed}/{self.workout.lapsPerInterval}"
                
                print(f"  {rs.runner.name:<20} {interval_num:<15} {progress:<15}")
            
            print("  " + "=" * 56)
            print(f"  Total running: {len(running_sessions)}")
            
        except Exception as e:
            print(f"  Error getting running athletes: {e}")
    
    # ========== OPTION 8: Terminate application ==========
    
    def terminate_application(self, args: List[str]):
        """Terminate the application."""
        print("\n  " + "=" * 56)
        print("  Thank you for using Interval Training Software!")
        print("  " + "=" * 56 + "\n")
    
    # ========== UTILITY: Show workout status ==========
    
    def show_workout_status(self, args: List[str] = None):
        """Show current workout status."""
        try:
            active, resting = self.workout.get_runner_counts()
            total = len(self.workout.runnerSessions)
            
            print("\n  " + "=" * 56)
            print("  WORKOUT STATUS")
            print("  " + "=" * 56)
            print(f"  Workout ID:    {self.workout.workout_id}")
            print(f"  Status:        {self.workout.status}")
            print(f"  Total Runners: {total}")
            print(f"  Active:        {active}")
            print(f"  Resting:       {resting}")
            print(f"  Not Started:   {total - active - resting}")
            print("  " + "=" * 56)
            
        except Exception as e:
            print(f"  Error getting workout status: {e}")


def main():
    """Main entry point."""
    cli = IntervalTrainingCLI()
    
    # Check for command line arguments for non-interactive mode
    if len(sys.argv) > 1:
        # Non-interactive mode - execute single command
        command = " ".join(sys.argv[1:])
        print(f"Executing: {command}")
        
        parts = command.split()
        menu_option = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        if menu_option in cli.menu_options:
            try:
                cli.menu_options[menu_option](args)
            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)
        else:
            print(f"Unknown command: {menu_option}")
            sys.exit(1)
    else:
        # Interactive mode
        try:
            cli.run()
        except KeyboardInterrupt:
            print("\n\nApplication terminated.")
        except Exception as e:
            print(f"Fatal error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()