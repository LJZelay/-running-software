"""
CSV Input Parser for Interval Training Software
Handles CSV file parsing and validation for workout rosters.
Connects CSV data to domain entities (Runner, Workout).
"""
import csv
import io
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from domain.entities.runner import Runner
from domain.entities.workout import Workout, WorkoutConfiguration
from domain.value_objects.nfc_id import NFCId
from domain.value_objects.rfid_id import RFIDId
from domain.value_objects.email import Email


class CSVInputError(Exception):
    """Custom exception for CSV input errors."""
    pass


class CSVInputParser:
    """
    Parses CSV files for runner roster data and validates against domain rules.
    """
    
    # Expected CSV column headers (case-insensitive)
    EXPECTED_COLUMNS = {
        'name', 'nfc_id', 'rfid_id', 'email', 'nfc', 'rfid',
        'Name', 'NFC ID', 'RFID ID', 'Email', 'NFC', 'RFID'
    }
    
    REQUIRED_COLUMNS = {'name', 'nfc_id', 'rfid_id'}
    
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
            
            'nfc_id': 'nfc_id',
            'nfc': 'nfc_id',
            'NFC ID': 'nfc_id',
            'NFC_ID': 'nfc_id',
            'NFC': 'nfc_id',
            
            'rfid_id': 'rfid_id',
            'rfid': 'rfid_id',
            'RFID ID': 'rfid_id',
            'RFID_ID': 'rfid_id',
            'RFID': 'rfid_id',
            
            'email': 'email',
            'Email': 'email',
            'EMAIL': 'email',
        }
        
        for header in headers:
            if header in header_mapping:
                normalized[header_mapping[header]] = header
            else:
                normalized[header] = header  # Keep original if not mapped
        
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
                if value:  # Only include non-empty values
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
        # Validate NFC ID
        if 'nfc_id' in row_data:
            try:
                NFCId(row_data['nfc_id'])
            except ValueError as e:
                raise CSVInputError(f"Invalid NFC ID '{row_data['nfc_id']}': {str(e)}")
        
        # Validate RFID ID
        if 'rfid_id' in row_data:
            try:
                RFIDId(row_data['rfid_id'])
            except ValueError as e:
                raise CSVInputError(f"Invalid RFID ID '{row_data['rfid_id']}': {str(e)}")
        
        # Validate email
        if 'email' in row_data and row_data['email']:
            try:
                Email(row_data['email'])
            except ValueError as e:
                raise CSVInputError(f"Invalid email '{row_data['email']}': {str(e)}")
        
        # Validate name (basic validation)
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
        
        Raises:
            CSVInputError: If data cannot be converted to Runner objects
        """
        runners = []
        errors = []
        
        for i, row in enumerate(csv_data, start=1):
            try:
                runner = self._create_runner_from_row(row, i)
                runners.append(runner)
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
    
    def _create_runner_from_row(self, row: Dict[str, Any], row_num: int) -> Runner:
        """Create a Runner object from a parsed row."""
        try:
            # Extract values
            name = row['name']
            nfc_id = NFCId(row['nfc_id'])
            rfid_id = RFIDId(row['rfid_id'])
            email = Email(row['email']) if row.get('email') else None
            
            # Create runner
            return Runner(
                name=name,
                nfc_id=nfc_id,
                rfid_id=rfid_id,
                email=email
            )
        except KeyError as e:
            raise CSVInputError(f"Missing field: {e}")
        except ValueError as e:
            raise CSVInputError(str(e))
    
    def validate_csv_for_workout(self, csv_data: List[Dict[str, Any]], workout_config: WorkoutConfiguration) -> Tuple[bool, List[str]]:
        """
        Validate CSV data for a specific workout configuration.
        
        Args:
            csv_data: Parsed CSV data
            workout_config: Workout configuration to validate against
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check if there are runners
        if not csv_data:
            errors.append("CSV file contains no runner data")
            return False, errors
        
        # Check for duplicate NFC/RFID IDs
        nfc_ids = set()
        rfid_ids = set()
        
        for i, row in enumerate(csv_data, start=1):
            # Check for duplicate NFC IDs
            if 'nfc_id' in row:
                nfc_id = row['nfc_id']
                if nfc_id in nfc_ids:
                    errors.append(f"Row {i}: Duplicate NFC ID: {nfc_id}")
                else:
                    nfc_ids.add(nfc_id)
            
            # Check for duplicate RFID IDs
            if 'rfid_id' in row:
                rfid_id = row['rfid_id']
                if rfid_id in rfid_ids:
                    errors.append(f"Row {i}: Duplicate RFID ID: {rfid_id}")
                else:
                    rfid_ids.add(rfid_id)
        
        return len(errors) == 0, errors


class CSVWorkoutImporter:
    """
    Higher-level service for importing CSV data into workout context.
    Connects CSV parsing with workout management
    """
    
    def __init__(self, csv_parser: CSVInputParser = None):
        self.csv_parser = csv_parser or CSVInputParser()
        self.imported_runners: List[Runner] = []
    
    def import_roster_to_workout(self, workout: Workout, csv_file_path: str) -> Tuple[Workout, List[Runner]]:
        """
        Import runners from CSV file into a workout.
        
        Args:
            workout: Workout to import runners into
            csv_file_path: Path to CSV roster file
            
        Returns:
            Tuple of (updated_workout, list_of_imported_runners)
        
        Raises:
            CSVInputError: If import fails
        """
        # Parse CSV file
        csv_data = self.csv_parser.parse_csv_file(csv_file_path)
        
        # Validate against workout
        if workout.configuration:
            is_valid, errors = self.csv_parser.validate_csv_for_workout(csv_data, workout.configuration)
            if not is_valid:
                raise CSVInputError(f"CSV validation failed: {', '.join(errors)}")
        
        # Create runners from CSV data
        runners = self.csv_parser.create_runners_from_csv(csv_data)
        
        # Add runners to workout
        added_runners = []
        for runner in runners:
            try:
                workout.add_runner(runner)
                added_runners.append(runner)
            except ValueError as e:
                if self.csv_parser.strict_validation:
                    raise CSVInputError(f"Failed to add runner {runner.name}: {str(e)}")
                else:
                    print(f"Warning: Skipping runner {runner.name} - {str(e)}")
        
        self.imported_runners = added_runners
        return workout, added_runners
    
    def import_roster_from_string(self, workout: Workout, csv_string: str) -> Tuple[Workout, List[Runner]]:
        """
        Import runners from CSV string into a workout.
        
        Args:
            workout: Workout to import runners into
            csv_string: CSV content as string
            
        Returns:
            Tuple of (updated_workout, list_of_imported_runners)
        """
        # Parse CSV string
        csv_data = self.csv_parser.parse_csv_string(csv_string)
        
        # Validate against workout
        if workout.configuration:
            is_valid, errors = self.csv_parser.validate_csv_for_workout(csv_data, workout.configuration)
            if not is_valid:
                raise CSVInputError(f"CSV validation failed: {', '.join(errors)}")
        
        # Create runners from CSV data
        runners = self.csv_parser.create_runners_from_csv(csv_data)
        
        # Add runners to workout
        added_runners = []
        for runner in runners:
            try:
                workout.add_runner(runner)
                added_runners.append(runner)
            except ValueError as e:
                if self.csv_parser.strict_validation:
                    raise CSVInputError(f"Failed to add runner {runner.name}: {str(e)}")
                else:
                    print(f"Warning: Skipping runner {runner.name} - {str(e)}")
        
        self.imported_runners = added_runners
        return workout, added_runners
    
    def export_workout_roster_to_csv(self, workout: Workout) -> str:
        """
        Export workout roster to CSV format string.
        
        Args:
            workout: Workout to export
            
        Returns:
            CSV content as string
        """
        if not workout.runners:
            return ""
        
        # Prepare CSV data
        fieldnames = ['name', 'nfc_id', 'rfid_id', 'email']
        rows = []
        
        for runner in workout.runners:
            row = {
                'name': runner.name,
                'nfc_id': str(runner.nfc_id),
                'rfid_id': str(runner.rfid_id),
                'email': str(runner.email) if runner.email else ''
            }
            rows.append(row)
        
        # Write to string
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
EXAMPLE_CSV_CONTENT = """name,nfc_id,rfid_id,email
John Doe,A1B2C3D4,E5F6A7B8C9D0,john.doe@example.com
Jane Smith,B2C3D4E5,F6A7B8C9D0E1,jane.smith@example.com
Bob Johnson,C3D4E5F6,A7B8C9D0E1F2,bob.johnson@example.com
Alice Wilson,D4E5F6A7,B8C9D0E1F2A3,alice.wilson@example.com
"""


def demonstrate_csv_parsing():
    """Demonstrate CSV parsing functionality."""
    print("=" * 60)
    print("CSV INPUT PARSER DEMONSTRATION")
    print("=" * 60)
    
    # Create parser
    parser = CSVInputParser(strict_validation=False)
    
    print("\n1. PARSING EXAMPLE CSV STRING:")
    try:
        csv_data = parser.parse_csv_string(EXAMPLE_CSV_CONTENT)
        print(f"  Successfully parsed {len(csv_data)} rows")
        for i, row in enumerate(csv_data[:2], 1):  # Show first 2 rows
            print(f"  Row {i}: {row}")
        if len(csv_data) > 2:
            print(f"  ... and {len(csv_data) - 2} more rows")
    except CSVInputError as e:
        print(f"  Error: {e}")
    
    print("\n2. CREATING RUNNER OBJECTS FROM CSV:")
    try:
        runners = parser.create_runners_from_csv(csv_data)
        print(f"  Created {len(runners)} runner objects:")
        for runner in runners[:2]:  # Show first 2 runners
            print(f"    - {runner.name}: NFC={runner.nfc_id}, RFID={runner.rfid_id}")
        if len(runners) > 2:
            print(f"    ... and {len(runners) - 2} more")
    except CSVInputError as e:
        print(f"  Error: {e}")
    
    print("\n3. TESTING VALIDATION:")
    # Test invalid CSV
    invalid_csv = """name,nfc_id,rfid_id,email
John Doe,INVALID_NFC,E5F6A7B8C9D0,john@example.com
,J,K,
Valid Person,F6A7B8C9D0E1,G7H8I9J0K1L2,valid@example.com
"""
    
    print("  Testing invalid CSV data:")
    try:
        invalid_data = parser.parse_csv_string(invalid_csv)
        print(f"  Parsed {len(invalid_data)} rows (some may be filtered)")
        
        # Try to create runners
        runners = parser.create_runners_from_csv(invalid_data)
        print(f"  Successfully created {len(runners)} runners from invalid data")
        
        if parser.validation_errors:
            print("  Validation errors:")
            for error in parser.validation_errors[:3]:  # Show first 3 errors
                print(f"    - {error}")
            if len(parser.validation_errors) > 3:
                print(f"    ... and {len(parser.validation_errors) - 3} more")
        
    except CSVInputError as e:
        print(f"  Error (expected): {e}")
    
    print("\n4. WORKOUT IMPORT DEMONSTRATION:")
    # Create a sample workout
    config = WorkoutConfiguration(
        name="Test Workout",
        interval_distance=400,
        rest_time=60,
        interval_count=8
    )
    
    workout = Workout(configuration=config)
    
    # Import roster
    importer = CSVWorkoutImporter()
    try:
        updated_workout, imported_runners = importer.import_roster_from_string(
            workout, EXAMPLE_CSV_CONTENT
        )
        print(f"  Imported {len(imported_runners)} runners into workout")
        print(f"  Workout now has {len(updated_workout.runners)} total runners")
    except CSVInputError as e:
        print(f"  Import error: {e}")
    
    print("\n5. CSV EXPORT DEMONSTRATION:")
    if workout.runners:
        csv_export = importer.export_workout_roster_to_csv(workout)
        print("  Exported CSV (first few lines):")
        lines = csv_export.split('\n')[:4]  # Show header + first 3 rows
        for line in lines:
            print(f"    {line}")
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    demonstrate_csv_parsing()