#!/usr/bin/env python3
"""
Enhanced Command Line Interface for Runners' Interval Workout Management Tool.
Supports:
- athletes.csv (roster loading)
- events.csv (workout event replay)
- workout_summary.csv (results export)
"""

import sys
import os
import csv
import time
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from domain import workout

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Application layer imports
from application.dto.runner_rest_view import RunnerRestView
from application.dto.runner_running_view import RunnerRunningView
from application.dto.runner_summary_view import RunnerSummaryView
from application.dto.workout_status_view import WorkoutStatusView
from application.exceptions import WorkoutNotFoundError, InvalidApplicationRequestError
from application.last_roster_service import LastRosterService

# Repository imports
from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository

# Try to import use cases, with fallbacks if they don't exist
try:
    from application.use_cases.start_workout import StartWorkoutUseCase
except ImportError:
    StartWorkoutUseCase = None

try:
    from application.use_cases.end_workout import EndWorkoutUseCase
except ImportError:
    EndWorkoutUseCase = None

try:
    from application.use_cases.scan_nfc import ScanNFCUseCase
except ImportError:
    ScanNFCUseCase = None

try:
    from application.use_cases.scan_rfid import ScanRFIDUseCase
except ImportError:
    ScanRFIDUseCase = None

try:
    from application.use_cases.group_start import GroupStartUseCase
except ImportError as e:
    print(f"Warning: Could not import GroupStartUseCase: {e}")
    GroupStartUseCase = None

try:
    from application.use_cases.get_rest_screen import GetRestScreenUseCase
except ImportError:
    GetRestScreenUseCase = None

try:
    from application.use_cases.get_running_screen import GetRunningScreenUseCase
except ImportError:
    GetRunningScreenUseCase = None

try:
    from application.use_cases.add_runner_to_workout import AddRunnerToWorkoutUseCase
except ImportError:
    AddRunnerToWorkoutUseCase = None

# External interface imports
try:
    from externalInterface.csv_roster_parser import CSVRosterParser, CSVInputError
except ImportError:
    # Define fallback if the module doesn't exist
    class CSVInputError(Exception):
        pass
    
    class CSVRosterParser:
        def parse_csv_file(self, file_path):
            raise NotImplementedError("CSVRosterParser not available")
        def validate_unique_tags(self, data):
            return True, []


class CSVEventError(Exception):
    """Exception for CSV event parsing errors."""
    pass


class WorkoutSummaryExporter:
    """Handles exporting workout results to CSV format."""
    
    @staticmethod
    def export_to_file(workout, file_path: str) -> bool:
        """
        Export workout summary to CSV file in the format shown in workout_summary.csv.
        """
        try:
            # Collect all data
            rows = []
            max_intervals = 0
            
            # First pass: find max intervals
            for rs in workout.runnerSessions:
                max_intervals = max(max_intervals, len(rs.intervals))
            
            # Create header
            header = ["Runner Name"]
            for i in range(1, max_intervals + 1):
                header.append(f"Interval {i} Duration (ms)")
                if i < max_intervals:  # No rest after last interval
                    header.append(f"Rest {i} Duration (ms)")
            
            # Create data rows
            for rs in workout.runnerSessions:
                row = [rs.runner.name]
                
                for i in range(max_intervals):
                    # Interval duration
                    if i < len(rs.intervals):
                        interval = rs.intervals[i]
                        if interval.get("start") and interval.get("end"):
                            start = datetime.fromisoformat(interval["start"])
                            end = datetime.fromisoformat(interval["end"])
                            duration_ms = int((end - start).total_seconds() * 1000)
                            row.append(str(duration_ms))
                        else:
                            row.append("0")
                    else:
                        row.append("0")
                    
                    # Rest duration (if not last interval)
                    if i < max_intervals - 1:
                        if i < len(rs.rests):
                            rest = rs.rests[i]
                            if rest.get("start") and rest.get("end"):
                                start = datetime.fromisoformat(rest["start"])
                                end = datetime.fromisoformat(rest["end"])
                                duration_ms = int((end - start).total_seconds() * 1000)
                                row.append(str(duration_ms))
                            else:
                                row.append("0")
                        else:
                            row.append("0")
                
                rows.append(row)
            
            # Write to file
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(rows)
            
            return True
            
        except Exception as e:
            print(f"  Error exporting summary: {e}")
            return False


class EventCSVProcessor:
    """Processes events.csv and executes them against a workout."""
    
    def __init__(self, cli):
        self.cli = cli
    
    def process_file(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Process events.csv file and execute events in chronological order.
        """
        errors = []
        
        try:
            # Read and parse events
            events = self._parse_events_file(file_path)
            if not events:
                return False, ["No events found in file"]
            
            # Sort events by timestamp
            events.sort(key=lambda e: e['timestamp'])
            
            print(f"\n  Processing {len(events)} events in chronological order...")
            
            # Process each event
            for i, event in enumerate(events, 1):
                success, error = self._process_event(event, i)
                if not success:
                    errors.append(f"Event {i}: {error}")
            
            return len(errors) == 0, errors
            
        except CSVEventError as e:
            return False, [str(e)]
        except Exception as e:
            return False, [f"Unexpected error: {e}"]
    
    def _parse_events_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse events.csv file."""
        events = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Check required columns
                if not reader.fieldnames:
                    raise CSVEventError("CSV file has no headers")
                
                required = {'TYPE', 'TIMESTAMP'}
                missing = required - set(reader.fieldnames)
                if missing:
                    raise CSVEventError(f"Missing required columns: {missing}")
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        event_type = row['TYPE'].strip().upper()
                        timestamp = row['TIMESTAMP'].strip()
                        tag = row.get('TAG', '').strip() if 'TAG' in row else ''
                        
                        # Validate
                        if not event_type:
                            raise CSVEventError(f"Row {row_num}: Empty TYPE")
                        
                        if not timestamp:
                            raise CSVEventError(f"Row {row_num}: Empty TIMESTAMP")
                        
                        # For GROUP, START events, TAG is optional
                        if event_type in ['NFC', 'RFID'] and not tag:
                            raise CSVEventError(f"Row {row_num}: {event_type} event missing TAG")
                        
                        events.append({
                            'type': event_type,
                            'timestamp': timestamp,
                            'tag': tag,
                            'row': row_num
                        })
                        
                    except Exception as e:
                        raise CSVEventError(f"Row {row_num}: {e}")
            
            return events
            
        except FileNotFoundError:
            raise CSVEventError(f"File not found: {file_path}")
        except Exception as e:
            raise CSVEventError(f"Error parsing file: {e}")
    
    def _process_event(self, event: Dict[str, Any], event_num: int) -> Tuple[bool, str]:
        """Process a single event."""
        event_type = event['type']
        timestamp = event['timestamp']
        tag = event['tag']
        
        # Convert timestamp to readable format for display
        try:
            timestamp_ms = int(timestamp)
            dt = datetime.fromtimestamp(timestamp_ms / 1000.0)
            time_str = dt.strftime('%H:%M:%S.%f')[:-3]
        except:
            dt = datetime.now()
            time_str = timestamp
        
        try:
            if event_type == 'GROUP':
                # Add athlete to group
                if tag:
                    # Find runner by NFC tag
                    runner_session = self.cli._find_runner_by_nfc(tag)
                    if runner_session:
                        if tag not in self.cli.group_nfc_tags:
                            self.cli.group_nfc_tags.append(tag)
                            print(f"    ✓ Event {event_num}: Added {runner_session.runner.name} to group (NFC: {tag}) at {time_str}")
                        else:
                            print(f"    - Event {event_num}: {runner_session.runner.name} already in group")
                    else:
                        print(f"    ⚠ Event {event_num}: Unknown NFC tag {tag} for GROUP event")
            
            elif event_type == 'START':
                # Trigger group start
                if self.cli.group_nfc_tags and self.cli.group_start_uc:
                    try:
                        started_count, active_count, resting_count = self.cli.group_start_uc.execute(
                            self.cli.workout_id
                        )
                        print(f"    ✓ Event {event_num}: Group start triggered at {time_str}")
                        print(f"      Started: {started_count}, Active: {active_count}, Resting: {resting_count}")
                        self.cli.group_nfc_tags.clear()
                    except Exception as e:
                        print(f"    ✗ Event {event_num}: Group start failed: {e}")
                else:
                    print(f"    ⚠ Event {event_num}: START event but no athletes in group or group start unavailable")
            
            elif event_type == 'NFC':
                # NFC scan to start interval
                if self.cli.scan_nfc_uc:
                    try:
                        status_view = self.cli.scan_nfc_uc.execute(
                            self.cli.workout_id,
                            tag,
                            dt.isoformat()
                        )
                        
                        # Find runner name for better display
                        runner_session = self.cli._find_runner_by_nfc(tag)
                        runner_name = runner_session.runner.name if runner_session else tag
                        
                        print(f"    ✓ Event {event_num}: NFC scan - {runner_name} started interval at {time_str}")
                        print(f"      Active: {status_view.active_runner_count}, Resting: {status_view.resting_runner_count}")
                        
                    except Exception as e:
                        print(f"    ✗ Event {event_num}: NFC scan failed for {tag}: {e}")
                else:
                    print(f"    ⚠ Event {event_num}: NFC scan use case not available")
            
            elif event_type == 'RFID':
                # RFID detection (lap/interval completion)
                if self.cli.scan_rfid_uc:
                    try:
                        status_view = self.cli.scan_rfid_uc.execute(
                            self.cli.workout_id,
                            tag,
                            dt.isoformat()
                        )
                        
                        # Find runner name for better display
                        runner_session = self.cli._find_runner_by_rfid(tag)
                        runner_name = runner_session.runner.name if runner_session else tag
                        
                        # Determine if lap or interval completion
                        if runner_session and runner_session.intervals:
                            laps_completed = len(runner_session.intervals[-1]["laps"]) if runner_session.intervals else 0
                            if laps_completed >= self.cli.workout_config['laps_per_interval']:
                                print(f"    ✓ Event {event_num}: RFID - {runner_name} COMPLETED INTERVAL at {time_str}")
                            else:
                                print(f"    ✓ Event {event_num}: RFID - {runner_name} completed lap {laps_completed} at {time_str}")
                        else:
                            print(f"    ✓ Event {event_num}: RFID detection - {tag} at {time_str}")
                        
                        print(f"      Active: {status_view.active_runner_count}, Resting: {status_view.resting_runner_count}")
                        
                    except Exception as e:
                        print(f"    ✗ Event {event_num}: RFID detection failed for {tag}: {e}")
                else:
                    print(f"    ⚠ Event {event_num}: RFID scan use case not available")
            
            else:
                print(f"    ⚠ Event {event_num}: Unknown event type: {event_type}")
            
            return True, ""
            
        except Exception as e:
            return False, f"Error processing {event_type} event: {e}"


class IntervalTrainingCLI:
    """
    Enhanced CLI with support for athletes.csv, events.csv, and workout_summary.csv
    """
    
    # Default workout configuration
    DEFAULT_WORKOUT_ID = 1
    DEFAULT_INTERVAL_DISTANCE = 400  # meters
    DEFAULT_LAPS_PER_INTERVAL = 1
    DEFAULT_REST_DURATION = 60  # seconds
    DEFAULT_START_MODE = "INDIVIDUAL"
    
    def __init__(self):
        """Initialize CLI with all dependencies."""
        # Initialize repository
        self.workout_repository = InMemoryWorkoutRepository()
        
        # Initialize CSV parser
        self.csv_parser = CSVRosterParser(strict_validation=True)

        #initialize last roster service
        self.last_roster_service = LastRosterService()
        
        # Initialize event processor
        self.event_processor = EventCSVProcessor(self)
        
        # Initialize summary exporter
        self.summary_exporter = WorkoutSummaryExporter()
        
        # Initialize use cases (with None checks)
        self._init_use_cases()
        
        # Current workout state
        self.workout_id = self.DEFAULT_WORKOUT_ID
        self.workout_config = {
            'interval_distance': self.DEFAULT_INTERVAL_DISTANCE,
            'rest_duration': self.DEFAULT_REST_DURATION,
            'laps_per_interval': self.DEFAULT_LAPS_PER_INTERVAL
        }
        
        # Create default workout
        self._create_default_workout()
        
        # Group members (NFC tags for group start)
        self.group_nfc_tags: List[str] = []
        
        # Menu mapping
        self.menu_options = {
            '1': self.cmd_configure_workout,
            '2': self.cmd_load_athletes_csv,
            '3': self.cmd_load_events_csv,
            '4': self.cmd_export_summary_csv,
            '5': self.cmd_add_to_group,
            '6': self.cmd_group_start,
            '7': self.cmd_simulate_rfid,
            '8': self.cmd_simulate_nfc,
            '9': self.cmd_show_resting,
            '10': self.cmd_show_running,
            '11': self.cmd_end_workout,
            '12': self.cmd_generate_report,
            '13': self.cmd_email_report,
            '14': self.cmd_exit,
            '15': self.cmd_load_last_roster,
            'help': self.cmd_help,
            'status': self.cmd_status,
            'group': self.cmd_show_group,
            'config': self.cmd_show_config,
            'runners': self.cmd_list_runners
        }
    
    def _init_use_cases(self):
        """Initialize all use cases with dependencies (if available)."""
        # Core workout use cases
        if StartWorkoutUseCase:
            self.start_workout_uc = StartWorkoutUseCase(self.workout_repository)
        else:
            self.start_workout_uc = None
            
        if EndWorkoutUseCase:
            self.end_workout_uc = EndWorkoutUseCase(self.workout_repository)
        else:
            self.end_workout_uc = None
        
        # Event handling use cases
        if ScanNFCUseCase:
            self.scan_nfc_uc = ScanNFCUseCase(self.workout_repository)
        else:
            self.scan_nfc_uc = None
            
        if ScanRFIDUseCase:
            self.scan_rfid_uc = ScanRFIDUseCase(self.workout_repository)
        else:
            self.scan_rfid_uc = None
        
        # Group start use case
        if GroupStartUseCase:
            self.group_start_uc = GroupStartUseCase(self.workout_repository)
        else:
            self.group_start_uc = None
            print("  Note: GroupStartUseCase not available - group start will be simulated")
        
        # Query use cases
        if GetRestScreenUseCase:
            self.get_rest_screen_uc = GetRestScreenUseCase(self.workout_repository)
        else:
            self.get_rest_screen_uc = None
            
        if GetRunningScreenUseCase:
            self.get_running_screen_uc = GetRunningScreenUseCase(self.workout_repository)
        else:
            self.get_running_screen_uc = None
        
        # Runner management use case
        if AddRunnerToWorkoutUseCase:
            self.add_runner_uc = AddRunnerToWorkoutUseCase(self.workout_repository)
        else:
            self.add_runner_uc = None
    
    def _create_default_workout(self):
        """Create default workout."""
        try:
            from domain.workout import Workout
            
            workout = Workout(
                workout_id=self.workout_id,
                intervalDistance=self.workout_config['interval_distance'],
                lapsPerInterval=self.workout_config['laps_per_interval'],
                startMode=self.DEFAULT_START_MODE
            )
            self.workout_repository.save(workout)
            print(f"\n✓ Created default workout (ID: {self.workout_id})")
        except Exception as e:
            print(f"✗ Failed to create default workout: {e}")
            sys.exit(1)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()
    
    def _find_runner_by_nfc(self, nfc_tag: str):
        """Find runner session by NFC tag."""
        workout = self.workout_repository.get_by_id(self.workout_id)
        if not workout:
            return None
        
        for rs in workout.runnerSessions:
            if rs.runner.nfc_tag == nfc_tag:
                return rs
        return None
    
    def _find_runner_by_rfid(self, rfid_tag: str):
        """Find runner session by RFID tag."""
        workout = self.workout_repository.get_by_id(self.workout_id)
        if not workout:
            return None
        
        for rs in workout.runnerSessions:
            if rs.runner.rfid_tag == rfid_tag:
                return rs
        return None
    
    def run(self):
        """Main CLI loop."""
        self._show_welcome()
        self.cmd_help()
        
        while True:
            try:
                command = input("\n❯ ").strip().lower()
                
                if not command:
                    continue
                
                parts = command.split()
                cmd = parts[0]
                args = parts[1:] if len(parts) > 1 else []
                
                if cmd in ['14', 'exit', 'quit', 'q']:
                    self.cmd_exit(args)
                    break
                
                if cmd in self.menu_options:
                    self.menu_options[cmd](args)
                else:
                    print(f"  Unknown command: {cmd}")
                    print("  Type 'help' to see available commands")
                    
            except KeyboardInterrupt:
                print("\n\n  Use 'exit' to quit")
            except WorkoutNotFoundError as e:
                print(f"  Workout error: {e}")
            except InvalidApplicationRequestError as e:
                print(f"  Invalid input: {e}")
            except Exception as e:
                print(f"  Unexpected error: {type(e).__name__}: {e}")
    
    def _show_welcome(self):
        """Display welcome message."""
        print("\n" + "=" * 60)
        print("   RUNNERS' INTERVAL WORKOUT MANAGEMENT TOOL")
        print("=" * 60)
        print("   Supports:")
        print("   • athletes.csv - Load roster")
        print("   • events.csv   - Replay workout events")
        print("   • workout_summary.csv - Export results")
        print("=" * 60)
    
    # ========== COMMAND: HELP ==========
    
    def cmd_help(self, args: List[str] = None):
        """Display help menu."""
        print("\n  AVAILABLE COMMANDS:")
        print("  " + "-" * 56)
        print("   CSV OPERATIONS:")
        print("   1               - Configure workout (distance, rest, laps)")
        print("   2 <filepath>    - Load athletes.csv roster")
        print("   3 <filepath>    - Load and replay events.csv")
        print("   4 <filepath>    - Export workout_summary.csv")
        print("\n   WORKOUT CONTROL:")
        print("   5 <nfc_tag>     - Add athlete to group")
        print("   6               - Trigger group start")
        print("   7 <rfid_tag>    - Simulate RFID detection")
        print("   8 <nfc_tag>     - Simulate NFC scan")
        print("   9               - Show resting athletes")
        print("   10              - Show running athletes")
        print("   11              - End current workout")
        print("\n   REPORTING:")
        print("   12              - Generate PDF report")
        print("   13              - Email report to participants")
        print("   14              - Exit application")
        print("   15              - Load last roster from previous session")
        print("\n   UTILITY:")
        print("   status         - Show workout status")
        print("   group          - Show current group members")
        print("   config         - Show workout configuration")
        print("   runners        - List all loaded runners")
        print("   help           - Show this help message")
        print("\n  EXAMPLES:")
        print("   2 data/athletes.csv")
        print("   3 data/events.csv")
        print("   4 data/workout_summary.csv")
        print("   5 NFC001")
        print("   6")
        print("=" * 60)
    
    # ========== COMMAND 1: Configure Workout ==========
    
    def cmd_configure_workout(self, args: List[str]):
        """Configure workout parameters."""
        print("\n--- WORKOUT CONFIGURATION ---")
        
        try:
            # Get interval distance
            current = self.workout_config['interval_distance']
            distance_input = input(f"Interval distance (meters) [{current}]: ").strip()
            if distance_input:
                self.workout_config['interval_distance'] = int(distance_input)
            
            # Get rest duration
            current = self.workout_config['rest_duration']
            rest_input = input(f"Rest time (seconds) [{current}]: ").strip()
            if rest_input:
                self.workout_config['rest_duration'] = int(rest_input)
            
            # Get laps per interval
            current = self.workout_config['laps_per_interval']
            laps_input = input(f"Laps per interval [{current}]: ").strip()
            if laps_input:
                self.workout_config['laps_per_interval'] = int(laps_input)
            
            # Update workout in repository
            workout = self.workout_repository.get_by_id(self.workout_id)
            if workout:
                workout.intervalDistance = self.workout_config['interval_distance']
                workout.lapsPerInterval = self.workout_config['laps_per_interval']
                self.workout_repository.save(workout)
            
            print("\n✓ Workout configured successfully")
            self.cmd_show_config()
            
        except ValueError as e:
            print(f"  Invalid input: {e}")
    
    # ========== COMMAND 2: Load athletes.csv ==========
    
    def cmd_load_athletes_csv(self, args: List[str]):
        """Load athletes.csv roster file."""
        if len(args) < 1:
            print("  Error: Missing file path. Usage: 2 <filepath>")
            return
        
        file_path = args[0]
        
        if not os.path.exists(file_path):
            print(f"  Error: File not found: {file_path}")
            return
        
        try:
            # Parse CSV file
            roster_data = self.csv_parser.parse_csv_file(file_path)
            
            # Validate unique tags
            is_valid, errors = self.csv_parser.validate_unique_tags(roster_data)
            if not is_valid:
                print("  CSV validation errors:")
                for error in errors:
                    print(f"    - {error}")
                return
            
            # Get current workout
            workout = self.workout_repository.get_by_id(self.workout_id)
            if not workout:
                print("  Error: Workout not found")
                return
            
            # Add each runner to workout
            added_count = 0
            for i, data in enumerate(roster_data):
                from domain.runner import Runner
                from domain.runnerSession import RunnerSession
                
                # Create runner
                runner = Runner(
                    runner_id=len(workout.runnerSessions) + i + 1,
                    name=data.name,
                    email=data.email or "",
                    nfc_tag=data.nfc_id,
                    rfid_tag=data.rfid_id
                )
                
                # Create session
                session = RunnerSession(
                    runner=runner,
                    restDuration=self.workout_config['rest_duration']
                )
                
                # Add to workout
                if workout.add_runner_session(session):
                    added_count += 1
            
            # Save workout
            self.workout_repository.save(workout)

            #save latest roster for next session
            print("  DEBUG: last roster save was called")
            saved_runners = [rs.runner for rs in workout.runnerSessions]
            self.last_roster_service.save_roster(saved_runners)
            print("DEBUG: save_roster call completed")
            
            print(f"\n  ✓ Loaded {added_count} athletes from {file_path}")
            print("\n  Imported athletes:")
            for i, rs in enumerate(workout.runnerSessions[-added_count:], 1):
                print(f"    {i}. {rs.runner.name} (NFC: {rs.runner.nfc_tag}, RFID: {rs.runner.rfid_tag})")
            
        except Exception as e:
            print(f"  Error loading roster: {e}")

    # ========== COMMAND 15: Load last roster from previous session ==========
    def cmd_load_last_roster(self, args: List[str]):
        """Load the last saved roster file."""
        try:
            if not self.last_roster_service.has_saved_roster():
                print("\n  No saved roster found.")
                return

            runners = self.last_roster_service.load_roster()

            workout = self.workout_repository.get_by_id(self.workout_id)
            if not workout:
                print("  Error: Workout not found")
                return

            # Optional safety: prevent duplicate loading
            if workout.runnerSessions:
                print("\n  Error: Runners are already loaded into the current workout.")
                print("  Start a fresh workout before loading the saved roster.")
                return

            added_count = 0

            for runner in runners:
                from domain.runnerSession import RunnerSession

                session = RunnerSession(
                    runner=runner,
                    restDuration=self.workout_config['rest_duration']
                )

                if workout.add_runner_session(session):
                    added_count += 1

            self.workout_repository.save(workout)

            # Save this as the last known roster
            #saved_runners = [rs.runner for rs in workout.runnerSessions]
            #self.last_roster_service.save_roster(saved_runners)

            print(f"\n  ✓ Loaded {added_count} runners from last saved roster")

            for i, rs in enumerate(workout.runnerSessions[-added_count:], 1):
                print(f"    {i}. {rs.runner.name} (NFC: {rs.runner.nfc_tag}, RFID: {rs.runner.rfid_tag})")

        except Exception as e:
            print(f"  Error loading last saved roster: {e}")
    
    # ========== COMMAND 3: Load events.csv ==========
    
    def cmd_load_events_csv(self, args: List[str]):
        """Load and replay events.csv file."""
        if len(args) < 1:
            print("  Error: Missing file path. Usage: 3 <filepath>")
            return
        
        file_path = args[0]
        
        if not os.path.exists(file_path):
            print(f"  Error: File not found: {file_path}")
            return
        
        print(f"\n  Loading events from: {file_path}")
        print("  " + "-" * 56)
        
        # Process events
        success, errors = self.event_processor.process_file(file_path)
        
        print("  " + "-" * 56)
        
        if success:
            print(f"  ✓ All events processed successfully")
        else:
            print(f"  ✗ Errors occurred:")
            for error in errors:
                print(f"    - {error}")
    
    # ========== COMMAND 4: Export workout_summary.csv ==========
    
    def cmd_export_summary_csv(self, args: List[str]):
        """Export workout summary to CSV file."""
        if len(args) < 1:
            print("  Error: Missing file path. Usage: 4 <filepath>")
            return
        
        file_path = args[0]
        
        try:
            # Get workout
            workout = self.workout_repository.get_by_id(self.workout_id)
            if not workout:
                print("  Error: Workout not found")
                return
            
            # Export summary
            success = self.summary_exporter.export_to_file(workout, file_path)
            
            if success:
                print(f"\n  ✓ Workout summary exported to: {file_path}")
                
                # Show preview
                print("\n  Preview:")
                print("  " + "-" * 56)
                for rs in workout.runnerSessions[:3]:
                    intervals = len(rs.intervals)
                    print(f"    {rs.runner.name}: {intervals} intervals completed")
                if len(workout.runnerSessions) > 3:
                    print(f"    ... and {len(workout.runnerSessions) - 3} more")
            else:
                print(f"\n  ✗ Failed to export summary")
            
        except Exception as e:
            print(f"  Error exporting summary: {e}")
    
    # ========== COMMAND 5: Add athlete to group ==========
    
    def cmd_add_to_group(self, args: List[str]):
        """Add athlete to group start by NFC tag."""
        if len(args) < 1:
            print("  Error: Missing NFC tag. Usage: 5 <nfc_tag>")
            return
        
        nfc_tag = args[0]
        
        try:
            # Find runner by NFC tag
            runner_session = self._find_runner_by_nfc(nfc_tag)
            
            if not runner_session:
                print(f"  Error: No athlete found with NFC tag: {nfc_tag}")
                print("  Tip: Load athletes.csv first (command 2)")
                return
            
            if nfc_tag in self.group_nfc_tags:
                print(f"  ✓ {runner_session.runner.name} is already in the group")
            else:
                self.group_nfc_tags.append(nfc_tag)
                print(f"  ✓ Added {runner_session.runner.name} to group")
            
            print(f"  Group size: {len(self.group_nfc_tags)} athletes")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # ========== COMMAND 6: Group start ==========
    
    def cmd_group_start(self, args: List[str]):
        """Start all athletes in the group simultaneously."""
        if not self.group_nfc_tags:
            print("  Error: No athletes in group")
            print("  Tip: Use command 5 <nfc_tag> to add athletes to the group first")
            return
        
        try:
            if self.group_start_uc:
                # Use the GroupStartUseCase
                started_count, active_count, resting_count = self.group_start_uc.execute(
                    self.workout_id
                )
                print(f"\n  ✓ Group start completed (via use case)")
            else:
                # Fallback simulation
                print(f"\n  ⚠ GroupStartUseCase not available - simulating group start")
                
                # Manually start each runner in the group
                workout = self.workout_repository.get_by_id(self.workout_id)
                if not workout:
                    print("  Error: Workout not found")
                    return
                
                # Start workout if not active
                if hasattr(workout, 'status') and workout.status.value == "NOT_STARTED":
                    workout.start()
                
                started_count = 0
                for nfc_tag in self.group_nfc_tags:
                    runner_session = self._find_runner_by_nfc(nfc_tag)
                    if runner_session:
                        try:
                            runner_session.start_interval()
                            started_count += 1
                            print(f"    ✓ Started {runner_session.runner.name}")
                        except Exception as e:
                            print(f"    ✗ Could not start {runner_session.runner.name}: {e}")
                
                self.workout_repository.save(workout)
                active_count, resting_count = workout.get_runner_counts()
            
            self.group_nfc_tags.clear()
            print(f"\n    Started: {started_count} athletes")
            print(f"    Now active: {active_count}")
            print(f"    Now resting: {resting_count}")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # ========== COMMAND 7: Simulate RFID detection ==========
    
    def cmd_simulate_rfid(self, args: List[str]):
        """Simulate RFID detection event."""
        if len(args) < 1:
            print("  Error: Missing RFID tag. Usage: 7 <rfid_tag>")
            return
        
        rfid_tag = args[0]
        timestamp = self._get_timestamp()
        
        try:
            if self.scan_rfid_uc:
                status_view = self.scan_rfid_uc.execute(
                    self.workout_id,
                    rfid_tag,
                    timestamp
                )
                
                # Find runner name
                runner_session = self._find_runner_by_rfid(rfid_tag)
                runner_name = runner_session.runner.name if runner_session else rfid_tag
                
                print(f"\n  ✓ RFID: {runner_name} detected at {timestamp}")
                print(f"    Active: {status_view.active_runner_count}")
                print(f"    Resting: {status_view.resting_runner_count}")
            else:
                print(f"\n  ⚠ ScanRFIDUseCase not available")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # ========== COMMAND 8: Simulate NFC scan ==========
    
    def cmd_simulate_nfc(self, args: List[str]):
        """Simulate NFC scan event."""
        if len(args) < 1:
            print("  Error: Missing NFC tag. Usage: 8 <nfc_tag>")
            return
        
        nfc_tag = args[0]
        timestamp = self._get_timestamp()
        
        try:
            if self.scan_nfc_uc:
                status_view = self.scan_nfc_uc.execute(
                    self.workout_id,
                    nfc_tag,
                    timestamp
                )
                
                # Find runner name
                runner_session = self._find_runner_by_nfc(nfc_tag)
                runner_name = runner_session.runner.name if runner_session else nfc_tag
                
                print(f"\n  ✓ NFC: {runner_name} scanned at {timestamp}")
                print(f"    Active: {status_view.active_runner_count}")
                print(f"    Resting: {status_view.resting_runner_count}")
            else:
                print(f"\n  ⚠ ScanNFCUseCase not available")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # ========== COMMAND 9: Show resting athletes ==========
    
    def cmd_show_resting(self, args: List[str]):
        """Show resting athletes."""
        try:
            if self.get_rest_screen_uc:
                rest_views: List[RunnerRestView] = self.get_rest_screen_uc.execute(
                    self.workout_id
                )
            else:
                # Fallback
                workout = self.workout_repository.get_by_id(self.workout_id)
                rest_data = workout.get_rest_screen() if workout else []
                rest_views = []
                for data in rest_data:
                    rest_views.append(RunnerRestView(
                        runner_id=data["runner_id"],
                        runner_name=data["runner_name"],
                        remaining_rest_seconds=data["remaining_seconds"],
                        is_ready_to_run=False
                    ))
            
            if not rest_views:
                print("\n  No athletes currently resting.")
                return
            
            print("\n  " + "=" * 60)
            print("  RESTING ATHLETES")
            print("  " + "=" * 60)
            print(f"  {'Name':<20} {'Remaining':<15} {'Ready':<10}")
            print("  " + "-" * 60)
            
            for view in rest_views:
                mins = view.remaining_rest_seconds // 60
                secs = view.remaining_rest_seconds % 60
                time_str = f"{mins:02d}:{secs:02d}"
                ready_marker = "✓" if view.is_ready_to_run else " "
                
                print(f"  {view.runner_name:<20} {time_str:<15} {ready_marker:<10}")
            
            print("  " + "=" * 60)
            print(f"  Total resting: {len(rest_views)}")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # ========== COMMAND 10: Show running athletes ==========
    
    def cmd_show_running(self, args: List[str]):
        """Show running athletes."""
        try:
            if self.get_running_screen_uc:
                running_views: List[RunnerRunningView] = self.get_running_screen_uc.execute(
                    self.workout_id
                )
            else:
                # Fallback
                workout = self.workout_repository.get_by_id(self.workout_id)
                running_views = []
                if workout:
                    for rs in workout.runnerSessions:
                        if rs.state.value == "RUNNING":
                            interval_number = len(rs.intervals)
                            laps_completed = len(rs.intervals[-1]["laps"]) if rs.intervals else 0
                            running_views.append(RunnerRunningView(
                                runner_id=rs.runner.id,
                                runner_name=rs.runner.name,
                                interval_number=interval_number,
                                laps_completed=laps_completed,
                                laps_per_interval=self.workout_config['laps_per_interval']
                            ))
            
            if not running_views:
                print("\n  No athletes currently running.")
                return
            
            print("\n  " + "=" * 60)
            print("  RUNNING ATHLETES")
            print("  " + "=" * 60)
            print(f"  {'Name':<20} {'Interval':<12} {'Progress':<15}")
            print("  " + "-" * 60)
            
            for view in running_views:
                interval_str = f"{view.interval_number}"
                progress_str = f"{view.laps_completed}/{view.laps_per_interval} laps"
                bar = view.progress_bar
                
                print(f"  {view.runner_name:<20} {interval_str:<12} {progress_str:<15}")
                print(f"  {' ':<20} {bar:<27} {view.progress_percentage:.0f}%")
            
            print("  " + "=" * 60)
            print(f"  Total running: {len(running_views)}")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # ========== COMMAND 11: End workout ==========
    
    def cmd_end_workout(self, args: List[str]):
        """End current workout."""
        try:
            if self.end_workout_uc:
                ended = self.end_workout_uc.execute(self.workout_id)
                
                if ended:
                    print("\n  ✓ Workout ended successfully")
                    self.cmd_status()
                else:
                    print("\n  ✗ Failed to end workout")
            else:
                # Fallback
                workout = self.workout_repository.get_by_id(self.workout_id)
                if workout:
                    workout.end()
                    self.workout_repository.save(workout)
                    print("\n  ✓ Workout ended successfully (simulated)")
                else:
                    print("\n  ✗ Failed to end workout")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # ========== COMMAND 12: Generate PDF report ==========
    
    def cmd_generate_report(self, args: List[str]):
        """Generate PDF report."""
        print("\n  📄 PDF Report Generation")
        print("  " + "-" * 56)
        print("  This would generate a PDF report with:")
        print("  • Runner names and dates")
        print("  • Interval distances and rest durations")
        print("  • Split times for each interval")
        print("  • Average paces")
        print("\n  [To be implemented with GenerateReportUseCase]")
    
    # ========== COMMAND 13: Email report ==========
    
    def cmd_email_report(self, args: List[str]):
        """Email report to participants."""
        print("\n  📧 Email Reports")
        print("  " + "-" * 56)
        print("  This would email reports to:")
        
        workout = self.workout_repository.get_by_id(self.workout_id)
        if workout:
            for rs in workout.runnerSessions:
                if rs.runner.email:
                    print(f"  • {rs.runner.name} <{rs.runner.email}>")
        
        print("\n  [Bonus feature - to be implemented with EmailReportUseCase]")
    
    # ========== COMMAND 14: Exit ==========
    
    def cmd_exit(self, args: List[str]):
        """Exit the application."""
        print("\n  " + "=" * 56)
        print("  Thank you for using the Interval Workout Management Tool!")
        print("  " + "=" * 56 + "\n")
    
    # ========== UTILITY: List all runners ==========
    
    def cmd_list_runners(self, args: List[str] = None):
        """List all loaded runners."""
        workout = self.workout_repository.get_by_id(self.workout_id)
        if not workout or not workout.runnerSessions:
            print("\n  No runners loaded.")
            print("  Use command 2 to load athletes.csv")
            return
        
        print("\n  LOADED RUNNERS:")
        print("  " + "-" * 60)
        print(f"  {'Name':<15} {'NFC Tag':<10} {'RFID Tag':<10} {'State':<12}")
        print("  " + "-" * 60)
        
        for rs in workout.runnerSessions:
            state = rs.state.value if hasattr(rs.state, 'value') else str(rs.state)
            group_marker = "*" if rs.runner.nfc_tag in self.group_nfc_tags else " "
            print(f"  {group_marker} {rs.runner.name:<14} {rs.runner.nfc_tag:<10} {rs.runner.rfid_tag:<10} {state:<12}")
        
        print("  " + "-" * 60)
        print(f"  Total: {len(workout.runnerSessions)} runners  (* = in group)")
    
    # ========== UTILITY: Show group members ==========
    
    def cmd_show_group(self, args: List[str] = None):
        """Show current group members."""
        if not self.group_nfc_tags:
            print("\n  No athletes in the current group.")
            print("  Use command 5 <nfc_tag> to add athletes to the group.")
            return
        
        print("\n  CURRENT GROUP MEMBERS:")
        print("  " + "-" * 40)
        for nfc_tag in sorted(self.group_nfc_tags):
            runner_session = self._find_runner_by_nfc(nfc_tag)
            if runner_session:
                state = runner_session.state.value if hasattr(runner_session.state, 'value') else str(runner_session.state)
                print(f"    • {runner_session.runner.name} (NFC: {nfc_tag}) - {state}")
            else:
                print(f"    • Unknown runner (NFC: {nfc_tag})")
        print(f"\n  Total group members: {len(self.group_nfc_tags)}")
    
    # ========== UTILITY: Show workout status ==========
    
    def cmd_status(self, args: List[str] = None):
        """Show current workout status."""
        try:
            workout = self.workout_repository.get_by_id(self.workout_id)
            if not workout:
                print("  Error: Workout not found")
                return
            
            active, resting = workout.get_runner_counts()
            total = len(workout.runnerSessions)
            not_started = total - active - resting
            
            status_view = WorkoutStatusView(
                workout_id=self.workout_id,
                workout_state=workout.status.value if hasattr(workout.status, 'value') else str(workout.status),
                active_runner_count=active,
                resting_runner_count=resting
            )
            
            print("\n  " + "=" * 56)
            print("  WORKOUT STATUS")
            print("  " + "=" * 56)
            print(f"  Workout ID:    {status_view.workout_id}")
            print(f"  State:         {status_view.workout_state}")
            print(f"  Total Runners: {total}")
            print(f"  Group Members: {len(self.group_nfc_tags)}")
            print(f"  Active:        {status_view.active_runner_count}")
            print(f"  Resting:       {status_view.resting_runner_count}")
            print(f"  Not Started:   {not_started}")
            print("  " + "=" * 56)
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # ========== UTILITY: Show workout configuration ==========
    
    def cmd_show_config(self, args: List[str] = None):
        """Show current workout configuration."""
        print("\n  WORKOUT CONFIGURATION:")
        print(f"    • Interval distance: {self.workout_config['interval_distance']} meters")
        print(f"    • Rest duration:     {self.workout_config['rest_duration']} seconds")
        print(f"    • Laps per interval: {self.workout_config['laps_per_interval']}")


def main():
    """Main entry point."""
    cli = IntervalTrainingCLI()
    
    if len(sys.argv) > 1:
        # Command line mode
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