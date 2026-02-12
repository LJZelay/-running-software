"""
CSV Input Parser for Interval Training Software
Handles CSV file parsing and validation for workout rosters.
Connects CSV data to domain entities (Runner, Workout).
"""
import csv
import io
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.workout import Workout


class CSVInputError(Exception):
    """Custom exception for CSV input errors."""
    pass


class CSVInputParser:
    """
    Parses CSV files for runner roster data and validates against domain rules.
    """
    
    # Expected CSV column headers (case-insensitive)
    EXPECTED_COLUMNS = {
        'name', 'nfc_tag', 'rfid_tag', 'email', 'nfc', 'rfid',
        'Name', 'NFC Tag', 'RFID Tag', 'Email', 'NFC', 'RFID'
    }
    
    REQUIRED_COLUMNS = {'name', 'nfc_tag', 'rfid_tag'}
    
    def __init__(self, strict_validation: bool = True):
        """
        Initialize CSV parser.
        
        Args:
            strict_validation: If True, raises exceptions for validation errors.
                               If False, collects errors but continues processing.
        """
        self.strict_validation = strict_validation
        self.validation_errors: List[str] = []
        self.warnings: List[str] = []
    
    def parse_csv_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse a CSV file and return list of dictionaries.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of dictionaries representing each row
            
        Raises:
            CSVInputError: If file cannot be read or parsed
        """
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as file:
                return self._parse_csv_content(file)
        except FileNotFoundError:
            raise CSVInputError(f"File not found: {file_path}")
        except PermissionError:
            raise CSVInputError(f"Permission denied: {file_path}")
        except Exception as e:
            raise CSVInputError(f"Error reading CSV file: {str(e)}")
    
    def parse_csv_string(self, csv_string: str) -> List[Dict[str, Any]]:
        """
        Parse CSV content from a string.
        
        Args:
            csv_string: CSV content as string
            
        Returns:
            List of dictionaries representing each row
        """
        file_like = io.StringIO(csv_string)
        return self._parse_csv_content(file_like)
    
    def _parse_csv_content(self, file_obj) -> List[Dict[str, Any]]:
        """Internal method to parse CSV content from file-like object."""
        self.validation_errors.clear()
        self.warnings.clear()
        
        # Read CSV
        try:
            reader = csv.DictReader(file_obj)
            rows = list(reader)
        except csv.Error as e:
            raise CSVInputError(f"CSV parsing error: {str(e)}")
        
        if not rows:
            raise CSVInputError("CSV file is empty")
        
        # Validate headers
        headers = reader.fieldnames or []
        normalized_headers = self._normalize_headers(headers)
        self._validate_headers(normalized_headers)
        
        if self.validation_errors and self.strict_validation:
            raise CSVInputError(f"Header validation failed: {self.validation_errors[0]}")
        
        # Process rows
        processed_rows = []
        for i, row in enumerate(rows, start=1):
            try:
                processed_row = self._process_row(row, normalized_headers, i)
                if processed_row:
                    processed_rows.append(processed_row)
            except CSVInputError as e:
                if self.strict_validation:
                    raise
                else:
                    self.validation_errors.append(f"Row {i}: {str(e)}")
        
        return processed_rows
    
    def _normalize_headers(self, headers: List[str]) -> Dict[str, str]:
        """Normalize CSV headers to standard field names."""
        normalized = {}
        
        # Mapping of possible header names to standard names
        header_mapping = {
            'name': 'name',
            'Name': 'name',
            'NAME': 'name',
            
            'nfc_tag': 'nfc_tag',
            'nfc': 'nfc_tag',
            'NFC Tag': 'nfc_tag',
            'NFC_TAG': 'nfc_tag',
            'NFC': 'nfc_tag',
            
            'rfid_tag': 'rfid_tag',
            'rfid': 'rfid_tag',
            'RFID Tag': 'rfid_tag',
            'RFID_TAG': 'rfid_tag',
            'RFID': 'rfid_tag',
            
            'email': 'email',
            'Email': 'email',
            'EMAIL': 'email',
        }
        
        for header in headers:
            header_stripped = header.strip()
            if header_stripped in header_mapping:
                normalized[header_mapping[header_stripped]] = header_stripped
            else:
                normalized[header_stripped] = header_stripped
        
        return normalized
    
    def _validate_headers(self, normalized_headers: Dict[str, str]):
        """Validate that required headers are present."""
        present_headers = set(normalized_headers.keys())
        
        # Check for required columns
        for required in self.REQUIRED_COLUMNS:
            if required not in present_headers:
                self.validation_errors.append(f"Missing required column: {required}")
        
        # Warn about unexpected columns
        unexpected = present_headers - self.EXPECTED_COLUMNS
        for column in unexpected:
            self.warnings.append(f"Unexpected column: {column}")
    
    def _process_row(self, row: Dict[str, str], normalized_headers: Dict[str, str], row_num: int) -> Optional[Dict[str, Any]]:
        """
        Process a single CSV row.
        
        Args:
            row: Original row dictionary
            normalized_headers: Mapping of standard names to original headers
            row_num: Row number for error messages
            
        Returns:
            Processed row dictionary or None if invalid
        
        Raises:
            CSVInputError: If row validation fails
        """
        # Map row data to standard field names
        processed = {}
        
        # Extract values using normalized headers
        for std_field, orig_header in normalized_headers.items():
            if orig_header in row:
                value = row[orig_header].strip()
                if value:
                    processed[std_field] = value
        
        # Validate required fields
        for field in self.REQUIRED_COLUMNS:
            if field not in processed or not processed[field]:
                raise CSVInputError(f"Missing required field: {field}")
        
        # Validate field formats
        self._validate_row_data(processed, row_num)
        
        return processed
    
    def _validate_row_data(self, row_data: Dict[str, Any], row_num: int):
        """Validate individual field values."""
        # Validate NFC tag - must be non-empty string
        if 'nfc_tag' in row_data:
            nfc_value = row_data['nfc_tag']
            if not nfc_value or not isinstance(nfc_value, str):
                raise CSVInputError(f"Invalid NFC tag: must be a non-empty string")
            if len(nfc_value) < 4:
                raise CSVInputError(f"NFC tag '{nfc_value}' is too short (minimum 4 characters)")
        
        # Validate RFID tag - must be non-empty string
        if 'rfid_tag' in row_data:
            rfid_value = row_data['rfid_tag']
            if not rfid_value or not isinstance(rfid_value, str):
                raise CSVInputError(f"Invalid RFID tag: must be a non-empty string")
            if len(rfid_value) < 4:
                raise CSVInputError(f"RFID tag '{rfid_value}' is too short (minimum 4 characters)")
        
        # Validate email format if provided
        if 'email' in row_data and row_data['email']:
            email_value = row_data['email']
            if '@' not in email_value or '.' not in email_value:
                raise CSVInputError(f"Invalid email format: '{email_value}'")
        
        # Validate name
        if 'name' in row_data:
            name = row_data['name']
            if len(name) < 2:
                raise CSVInputError(f"Name '{name}' is too short (minimum 2 characters)")
            if len(name) > 100:
                raise CSVInputError(f"Name '{name}' is too long (maximum 100 characters)")
    
    def create_runners_from_csv(self, csv_data: List[Dict[str, Any]]) -> List[Runner]:
        """
        Create Runner objects from parsed CSV data.
        
        Args:
            csv_data: List of dictionaries from parse_csv_file/string
            
        Returns:
            List of Runner objects
        """
        runners = []
        errors = []
        
        # Generate runner IDs starting from 1
        next_runner_id = 1
        
        for i, row in enumerate(csv_data, start=1):
            try:
                runner = self._create_runner_from_row(row, i, next_runner_id)
                runners.append(runner)
                next_runner_id += 1
            except (ValueError, CSVInputError) as e:
                error_msg = f"Row {i}: Failed to create runner - {str(e)}"
                if self.strict_validation:
                    raise CSVInputError(error_msg)
                else:
                    errors.append(error_msg)
        
        if errors and not self.strict_validation:
            print(f"Created {len(runners)} runners with {len(errors)} errors:")
            for error in errors:
                print(f"  - {error}")
        
        return runners
    
    def _create_runner_from_row(self, row: Dict[str, Any], row_num: int, runner_id: int) -> Runner:
        """Create a Runner object from a parsed row."""
        try:
            name = row['name']
            nfc_tag = row['nfc_tag']
            rfid_tag = row['rfid_tag']
            email_value = row.get('email', '')
            
            return Runner(
                runner_id=runner_id,
                name=name,
                email=email_value,
                nfc_tag=nfc_tag,
                rfid_tag=rfid_tag
            )
        except KeyError as e:
            raise CSVInputError(f"Missing field: {e}")
        except Exception as e:
            raise CSVInputError(str(e))
    
    def create_runner_sessions_from_csv(self, 
                                        csv_data: List[Dict[str, Any]], 
                                        rest_duration: int = 60) -> List[RunnerSession]:
        """
        Create RunnerSession objects from parsed CSV data.
        
        Args:
            csv_data: List of dictionaries from parse_csv_file/string
            rest_duration: Default rest duration in seconds
            
        Returns:
            List of RunnerSession objects
        """
        runners = self.create_runners_from_csv(csv_data)
        runner_sessions = []
        
        for runner in runners:
            runner_session = RunnerSession(
                runner=runner,
                restDuration=rest_duration,
                state="NOT_STARTED"
            )
            runner_sessions.append(runner_session)
        
        return runner_sessions
    
    def validate_csv_for_duplicates(self, csv_data: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Validate CSV data for duplicate NFC/RFID tags within the file.
        
        Args:
            csv_data: Parsed CSV data
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not csv_data:
            errors.append("CSV file contains no runner data")
            return False, errors
        
        nfc_tags = set()
        rfid_tags = set()
        
        for i, row in enumerate(csv_data, start=1):
            if 'nfc_tag' in row:
                nfc_tag = row['nfc_tag']
                if nfc_tag in nfc_tags:
                    errors.append(f"Row {i}: Duplicate NFC tag: {nfc_tag}")
                else:
                    nfc_tags.add(nfc_tag)
            
            if 'rfid_tag' in row:
                rfid_tag = row['rfid_tag']
                if rfid_tag in rfid_tags:
                    errors.append(f"Row {i}: Duplicate RFID tag: {rfid_tag}")
                else:
                    rfid_tags.add(rfid_tag)
        
        return len(errors) == 0, errors


class CSVWorkoutImporter:
    """
    Higher-level service for importing CSV data into workout context.
    Connects CSV parsing with workout management.
    """
    
    def __init__(self, csv_parser: CSVInputParser = None, default_rest_duration: int = 60):
        self.csv_parser = csv_parser or CSVInputParser()
        self.default_rest_duration = default_rest_duration
        self.imported_runners: List[Runner] = []
        self.imported_sessions: List[RunnerSession] = []
    
    def import_roster_to_workout(self, workout: Workout, csv_file_path: str) -> Tuple[Workout, List[RunnerSession]]:
        """
        Import runners from CSV file into a workout.
        
        Args:
            workout: Workout to import runners into
            csv_file_path: Path to CSV roster file
            
        Returns:
            Tuple of (updated_workout, list_of_imported_runner_sessions)
        """
        # Parse CSV file
        csv_data = self.csv_parser.parse_csv_file(csv_file_path)
        
        # Validate for duplicates within the CSV file
        is_valid, errors = self.csv_parser.validate_csv_for_duplicates(csv_data)
        if not is_valid:
            raise CSVInputError(f"CSV validation failed: {', '.join(errors)}")
        
        # Create runner sessions from CSV data
        runner_sessions = self.csv_parser.create_runner_sessions_from_csv(
            csv_data, self.default_rest_duration
        )
        
        # Add runner sessions to workout
        added_sessions = []
        for runner_session in runner_sessions:
            try:
                # Check for duplicate NFC in existing workout
                existing_nfc = workout._find_runner_session_by_nfc(runner_session.runner.nfc_tag)
                if existing_nfc:
                    if self.csv_parser.strict_validation:
                        raise CSVInputError(f"Runner with NFC tag {runner_session.runner.nfc_tag} already exists")
                    else:
                        print(f"Warning: Skipping runner {runner_session.runner.name} - NFC tag already exists")
                        continue
                
                # Check for duplicate RFID in existing workout
                existing_rfid = workout._find_runner_session_by_rfid(runner_session.runner.rfid_tag)
                if existing_rfid:
                    if self.csv_parser.strict_validation:
                        raise CSVInputError(f"Runner with RFID tag {runner_session.runner.rfid_tag} already exists")
                    else:
                        print(f"Warning: Skipping runner {runner_session.runner.name} - RFID tag already exists")
                        continue
                
                # Add to workout
                workout.add_runner_session(runner_session)
                added_sessions.append(runner_session)
                self.imported_runners.append(runner_session.runner)
                
            except ValueError as e:
                if self.csv_parser.strict_validation:
                    raise CSVInputError(f"Failed to add runner {runner_session.runner.name}: {str(e)}")
                else:
                    print(f"Warning: Skipping runner {runner_session.runner.name} - {str(e)}")
        
        self.imported_sessions = added_sessions
        return workout, added_sessions
    
    def import_roster_from_string(self, workout: Workout, csv_string: str) -> Tuple[Workout, List[RunnerSession]]:
        """
        Import runners from CSV string into a workout.
        
        Args:
            workout: Workout to import runners into
            csv_string: CSV content as string
        """
        csv_data = self.csv_parser.parse_csv_string(csv_string)
        
        is_valid, errors = self.csv_parser.validate_csv_for_duplicates(csv_data)
        if not is_valid:
            raise CSVInputError(f"CSV validation failed: {', '.join(errors)}")
        
        runner_sessions = self.csv_parser.create_runner_sessions_from_csv(
            csv_data, self.default_rest_duration
        )
        
        added_sessions = []
        for runner_session in runner_sessions:
            try:
                existing_nfc = workout._find_runner_session_by_nfc(runner_session.runner.nfc_tag)
                if existing_nfc:
                    if self.csv_parser.strict_validation:
                        raise CSVInputError(f"Runner with NFC tag {runner_session.runner.nfc_tag} already exists")
                    else:
                        print(f"Warning: Skipping runner {runner_session.runner.name} - NFC tag already exists")
                        continue
                
                existing_rfid = workout._find_runner_session_by_rfid(runner_session.runner.rfid_tag)
                if existing_rfid:
                    if self.csv_parser.strict_validation:
                        raise CSVInputError(f"Runner with RFID tag {runner_session.runner.rfid_tag} already exists")
                    else:
                        print(f"Warning: Skipping runner {runner_session.runner.name} - RFID tag already exists")
                        continue
                
                workout.add_runner_session(runner_session)
                added_sessions.append(runner_session)
                self.imported_runners.append(runner_session.runner)
                
            except ValueError as e:
                if self.csv_parser.strict_validation:
                    raise CSVInputError(f"Failed to add runner {runner_session.runner.name}: {str(e)}")
                else:
                    print(f"Warning: Skipping runner {runner_session.runner.name} - {str(e)}")
        
        self.imported_sessions = added_sessions
        return workout, added_sessions
    
    def export_workout_roster_to_csv(self, workout: Workout) -> str:
        """
        Export workout roster to CSV format string.
        
        Args:
            workout: Workout to export
            
        Returns:
            CSV content as string
        """
        if not workout.runnerSessions:
            return ""
        
        fieldnames = ['name', 'nfc_tag', 'rfid_tag', 'email']
        rows = []
        
        for runner_session in workout.runnerSessions:
            runner = runner_session.runner
            row = {
                'name': runner.name,
                'nfc_tag': runner.nfc_tag,
                'rfid_tag': runner.rfid_tag,
                'email': runner.email if runner.email else ''
            }
            rows.append(row)
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
        return output.getvalue()
    
    def save_workout_roster_to_file(self, workout: Workout, file_path: str):
        """
        Save workout roster to CSV file.
        
        Args:
            workout: Workout to export
            file_path: Path to save CSV file
        """
        csv_content = self.export_workout_roster_to_csv(workout)
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            file.write(csv_content)


# Example CSV content for testing
EXAMPLE_CSV_CONTENT = """name,nfc_tag,rfid_tag,email
John Doe,NFC001,RFID001,john.doe@example.com
Jane Smith,NFC002,RFID002,jane.smith@example.com
Bob Johnson,NFC003,RFID003,bob.johnson@example.com
Alice Wilson,NFC004,RFID004,alice.wilson@example.com
"""


def demonstrate_csv_parsing():
    """Demonstrate CSV parsing functionality."""
    print("=" * 60)
    print("CSV INPUT PARSER DEMONSTRATION")
    print("=" * 60)
    
    parser = CSVInputParser(strict_validation=False)
    
    print("\n1. PARSING EXAMPLE CSV STRING:")
    try:
        csv_data = parser.parse_csv_string(EXAMPLE_CSV_CONTENT)
        print(f"  Successfully parsed {len(csv_data)} rows")
        for i, row in enumerate(csv_data[:2], 1):
            print(f"  Row {i}: {row}")
        if len(csv_data) > 2:
            print(f"  ... and {len(csv_data) - 2} more rows")
    except CSVInputError as e:
        print(f"  Error: {e}")
    
    print("\n2. CREATING RUNNER OBJECTS FROM CSV:")
    try:
        runners = parser.create_runners_from_csv(csv_data)
        print(f"  Created {len(runners)} runner objects:")
        for runner in runners[:2]:
            print(f"    - {runner.name}: NFC={runner.nfc_tag}, RFID={runner.rfid_tag}")
        if len(runners) > 2:
            print(f"    ... and {len(runners) - 2} more")
    except CSVInputError as e:
        print(f"  Error: {e}")
    
    print("\n3. CREATING RUNNER SESSIONS FROM CSV:")
    try:
        runner_sessions = parser.create_runner_sessions_from_csv(csv_data, rest_duration=60)
        print(f"  Created {len(runner_sessions)} runner sessions:")
        for session in runner_sessions[:2]:
            print(f"    - {session.runner.name}: Rest={session.restDuration}s, State={session.state}")
        if len(runner_sessions) > 2:
            print(f"    ... and {len(runner_sessions) - 2} more")
    except CSVInputError as e:
        print(f"  Error: {e}")
    
    print("\n4. VALIDATING DUPLICATES:")
    duplicate_csv = """name,nfc_tag,rfid_tag,email
John Doe,NFC001,RFID001,john@example.com
Jane Smith,NFC001,RFID002,jane@example.com
"""
    try:
        duplicate_data = parser.parse_csv_string(duplicate_csv)
        is_valid, errors = parser.validate_csv_for_duplicates(duplicate_data)
        print(f"  Duplicate validation: {'PASSED' if is_valid else 'FAILED'}")
        if errors:
            for error in errors:
                print(f"    - {error}")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    demonstrate_csv_parsing()