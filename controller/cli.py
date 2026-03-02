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
from typing import List, Set
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Domain imports
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.workout import Workout

# Application layer imports
from application.csvWorkoutImporter import CSVWorkoutImporter
from externalInterface.csv_roster_parser import CSVInputError

# Repository
from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository

# Use Cases that exist
from application.use_cases.start_workout import StartWorkoutUseCase
from application.use_cases.scan_nfc import ScanNFCUseCase
from application.use_cases.scan_rfid import ScanRFIDUseCase
from application.use_cases.get_rest_screen import GetRestScreenUseCase
from application.use_cases.end_workout import EndWorkoutUseCase


class IntervalTrainingCLI:
    """
    Command Line Interface for Interval Training Software.
    """
    
    # Default workout configuration
    DEFAULT_WORKOUT_ID = 1
    DEFAULT_INTERVAL_DISTANCE = 400
    DEFAULT_LAPS_PER_INTERVAL = 1
    DEFAULT_REST_DURATION = 60
    DEFAULT_START_MODE = "INDIVIDUAL"
    
    def __init__(self):
        """Initialize CLI with default workout."""
        # Repository
        self.repository = InMemoryWorkoutRepository()
        
        # Use cases
        self.start_workout_uc = StartWorkoutUseCase(self.repository)
        self.scan_nfc_uc = ScanNFCUseCase(self.repository)
        self.scan_rfid_uc = ScanRFIDUseCase(self.repository)
        self.get_rest_screen_uc = GetRestScreenUseCase(self.repository)
        self.end_workout_uc = EndWorkoutUseCase(self.repository)
        
        # CSV utilities
        self.csv_importer = CSVWorkoutImporter()
        
        # Current workout
        self.workout = None
        self._create_default_workout()
        
        # Track group members (NFC tags)
        self.group_members: Set[str] = set()
        
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
            'status': self.show_workout_status,
            'group': self.show_group_members
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
                
                parts = command.split()
                menu_option = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                
                if menu_option in ['8', 'exit', 'quit', 'q']:
                    self.terminate_application(args)
                    break
                
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
        print("   3              - Trigger group start (starts ONLY group members)")
        print("   4 <rfid_tag>    - Send RFID tag detected event (finish lap)")
        print("   5 <nfc_tag>     - Send NFC tag scanned event (start interval)")
        print("   6              - Get list of currently resting athletes")
        print("   7              - Get list of currently running athletes")
        print("   8              - Terminate application")
        print("  " + "-" * 56)
        print("   status         - Show current workout status")
        print("   group          - Show current group members")
        print("   help           - Show this help message")
        print("\n  EXAMPLES:")
        print("   1 data/athletes.csv")
        print("   2 NFC001")
        print("   3")
        print("   4 RFID001")
        print("   5 NFC002")
        print("=" * 60)
    
    def show_group_members(self, args: List[str] = None):
        """Show current group members."""
        if not self.group_members:
            print("\n  No athletes in the current group.")
            print("  Use option 2 <nfc_tag> to add athletes to the group.")
            return
        
        print("\n  CURRENT GROUP MEMBERS:")
        print("  " + "-" * 40)
        for nfc_tag in sorted(self.group_members):
            runner_session = self.workout._find_runner_session_by_nfc(nfc_tag)
            if runner_session:
                print(f"    • {runner_session.runner.name} (NFC: {nfc_tag}) - {runner_session.state}")
            else:
                print(f"    • Unknown runner (NFC: {nfc_tag})")
        print(f"\n  Total group members: {len(self.group_members)}")
    
    # ========== OPTION 1: Load athletes from CSV ==========
    
    def load_athletes_from_csv(self, args: List[str]):
        """Load athletes from CSV file. Usage: 1 <filepath>"""
        if len(args) < 1:
            print("  Error: Missing file path. Usage: 1 <filepath>")
            return
        
        file_path = args[0]
        
        if not os.path.exists(file_path):
            print(f"  Error: File not found: {file_path}")
            return
        
        try:
            # Import roster using CSVWorkoutImporter
            updated_workout, runner_sessions = self.csv_importer.import_roster_to_workout(
                self.workout,
                file_path,
                self.DEFAULT_REST_DURATION,
                starting_runner_id=len(self.workout.runnerSessions) + 1
            )
            
            # Update workout reference and save
            self.workout = updated_workout
            self.repository.save(self.workout)
            
            added_count = len(runner_sessions)
            print(f"\n  ✓ Loaded {added_count} athletes from {file_path}")
            print(f"  Total athletes in workout: {len(self.workout.runnerSessions)}")
            
            if added_count > 0:
                print("\n  Imported athletes:")
                for rs in runner_sessions[:3]:
                    print(f"    - {rs.runner.name} (NFC: {rs.runner.nfc_tag}, RFID: {rs.runner.rfid_tag})")
                if added_count > 3:
                    print(f"    ... and {added_count - 3} more")
                    
        except CSVInputError as e:
            print(f"  Error loading CSV: {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")
    
    # ========== OPTION 2: Add athlete to group ==========
    
    def add_athlete_to_group(self, args: List[str]):
        """Add athlete to group by NFC tag. Usage: 2 <nfc_tag>"""
        if len(args) < 1:
            print("  Error: Missing NFC tag. Usage: 2 <nfc_tag>")
            return
        
        nfc_tag = args[0]
        
        try:
            runner_session = self.workout._find_runner_session_by_nfc(nfc_tag)
            
            if not runner_session:
                print(f"  Error: No athlete found with NFC tag: {nfc_tag}")
                print("  Tip: Load athletes from CSV first (option 1)")
                return
            
            if nfc_tag in self.group_members:
                print(f"  ✓ Athlete {runner_session.runner.name} is already in the group")
            else:
                self.group_members.add(nfc_tag)
                print(f"  ✓ Added {runner_session.runner.name} to group (NFC: {nfc_tag})")
            
            print(f"  Group size: {len(self.group_members)} athletes")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # ========== OPTION 3: Trigger group start ==========
    
    def trigger_group_start(self, args: List[str]):
        """Start ONLY the athletes that have been added to the group. Usage: 3"""
        if not self.group_members:
            print("  Error: No athletes in group")
            print("  Tip: Use option 2 <nfc_tag> to add athletes to the group first")
            return
        
        try:
            if self.workout.status == "NOT_STARTED":
                self.workout.start()
                print("  ✓ Workout started")
            
            started_count = 0
            skipped_count = 0
            
            for nfc_tag in list(self.group_members):
                runner_session = self.workout._find_runner_session_by_nfc(nfc_tag)
                
                if not runner_session:
                    print(f"  Warning: No runner found for NFC tag {nfc_tag} (removing from group)")
                    self.group_members.remove(nfc_tag)
                    continue
                
                if runner_session.state in ["NOT_STARTED", "READY"]:
                    try:
                        runner_session.start_interval()
                        started_count += 1
                        print(f"    ✓ {runner_session.runner.name} started interval {len(runner_session.intervals)}")
                    except ValueError as e:
                        print(f"    ✗ Could not start {runner_session.runner.name}: {e}")
                        skipped_count += 1
                else:
                    print(f"    - {runner_session.runner.name} is {runner_session.state} (cannot start)")
                    skipped_count += 1
            
            self.repository.save(self.workout)
            
            active, resting = self.workout.get_runner_counts()
            print(f"\n  ✓ Group start completed")
            print(f"    Started: {started_count} athletes")
            print(f"    Skipped: {skipped_count} athletes")
            print(f"    Active: {active}")
            print(f"    Resting: {resting}")
            
        except Exception as e:
            print(f"  Error starting group: {e}")
    
    # ========== OPTION 4: Send RFID event ==========
    
    def send_rfid_event(self, args: List[str]):
        """Send RFID tag detected event. Usage: 4 <rfid_tag>"""
        if len(args) < 1:
            print("  Error: Missing RFID tag. Usage: 4 <rfid_tag>")
            return
        
        rfid_tag = args[0]
        
        try:
            if self.workout.status != "ACTIVE":
                print("  Error: Workout is not active")
                print("  Tip: Trigger group start first (option 3)")
                return
            
            rs = self.workout._find_runner_session_by_rfid(rfid_tag)
            if not rs:
                print(f"  Error: No athlete found with RFID tag: {rfid_tag}")
                return
            
            rs.record_lap()
            
            if rs.should_finish_interval(self.workout.lapsPerInterval):
                rs.finish_interval()
                print(f"  ✓ {rs.runner.name} completed interval {len(rs.intervals)}")
                print(f"    State: {rs.state}, Rest: {rs.get_remaining_restDuration()}s remaining")
            else:
                laps_completed = len(rs.intervals[-1]["laps"]) if rs.intervals else 0
                print(f"  ✓ {rs.runner.name} completed lap {laps_completed}/{self.workout.lapsPerInterval}")
            
            self.repository.save(self.workout)
            
            active, resting = self.workout.get_runner_counts()
            print(f"    Active: {active}, Resting: {resting}")
            
        except ValueError as e:
            print(f"  Error processing RFID event: {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")
    
    # ========== OPTION 5: Send NFC event ==========
    
    def send_nfc_event(self, args: List[str]):
        """Send NFC tag scanned event. Usage: 5 <nfc_tag>"""
        if len(args) < 1:
            print("  Error: Missing NFC tag. Usage: 5 <nfc_tag>")
            return
        
        nfc_tag = args[0]
        
        try:
            if self.workout.status != "ACTIVE":
                print("  Error: Workout is not active")
                print("  Tip: Trigger group start first (option 3)")
                return
            
            rs = self.workout._find_runner_session_by_nfc(nfc_tag)
            if not rs:
                print(f"  Error: No athlete found with NFC tag: {nfc_tag}")
                return
            
            rs.check_if_ready()
            rs.start_interval()
            
            print(f"  ✓ {rs.runner.name} started interval {len(rs.intervals)}")
            print(f"    State: {rs.state}")
            
            self.repository.save(self.workout)
            
            active, resting = self.workout.get_runner_counts()
            print(f"    Active: {active}, Resting: {resting}")
            
        except ValueError as e:
            print(f"  Error processing NFC scan: {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")
    
    # ========== OPTION 6: Get resting athletes ==========
    
    def get_resting_athletes(self, args: List[str]):
        """Get list of currently resting athletes. Usage: 6"""
        try:
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
                
                rs = None
                for session in self.workout.runnerSessions:
                    if session.runner.id == data["runner_id"]:
                        rs = session
                        break
                
                interval_num = len(rs.intervals) if rs else 0
                group_marker = "*" if rs and rs.runner.nfc_tag in self.group_members else " "
                
                print(f"  {group_marker} {data['runner_name']:<18} {time_str:<15} {interval_num:<10}")
            
            print("  " + "=" * 56)
            print(f"  Total resting: {len(rest_data)}  (* = group member)")
            
        except Exception as e:
            print(f"  Error getting rest screen: {e}")
    
    # ========== OPTION 7: Get running athletes ==========
    
    def get_running_athletes(self, args: List[str]):
        """Get list of currently running athletes. Usage: 7"""
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
                group_marker = "*" if rs.runner.nfc_tag in self.group_members else " "
                
                print(f"  {group_marker} {rs.runner.name:<18} {interval_num:<15} {progress:<15}")
            
            print("  " + "=" * 56)
            print(f"  Total running: {len(running_sessions)}  (* = group member)")
            
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
            not_started = total - active - resting
            
            print("\n  " + "=" * 56)
            print("  WORKOUT STATUS")
            print("  " + "=" * 56)
            print(f"  Workout ID:    {self.workout.workout_id}")
            print(f"  Status:        {self.workout.status}")
            print(f"  Total Runners: {total}")
            print(f"  Group Members: {len(self.group_members)}")
            print(f"  Active:        {active}")
            print(f"  Resting:       {resting}")
            print(f"  Not Started:   {not_started}")
            print("  " + "=" * 56)
            
        except Exception as e:
            print(f"  Error getting workout status: {e}")


def main():
    """Main entry point."""
    cli = IntervalTrainingCLI()
    
    if len(sys.argv) > 1:
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
        try:
            cli.run()
        except KeyboardInterrupt:
            print("\n\nApplication terminated.")
        except Exception as e:
            print(f"Fatal error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()