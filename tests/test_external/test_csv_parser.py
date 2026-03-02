"""Unit tests for CSV roster parser."""
import pytest
from pathlib import Path
import csv
from externalInterface.csv_roster_parser import CSVRosterParser, RosterData, CSVInputError


# Path to actual test data
DATA_DIR = Path(__file__).parent.parent.parent / "data"
ATHLETES_CSV = DATA_DIR / "athletes.csv"


@pytest.mark.external
class TestCSVParserParsing:
    """Test CSV parsing functionality."""
    
    def test_parse_csv_file_with_valid_data(self):
        """Test parsing a valid CSV file with actual athlete data."""
        parser = CSVRosterParser(strict_validation=False)
        roster_data = parser.parse_csv_file(str(ATHLETES_CSV))
        
        # athletes.csv has 6 athletes
        assert len(roster_data) == 6
        assert roster_data[0].name == "Alice"
        assert roster_data[0].nfc_id == "NFC001"
        assert roster_data[1].name == "Bob"
        assert roster_data[1].nfc_id == "NFC002"
    
    def test_parse_csv_string_with_header_variants(self):
        """Test parsing CSV with header name variants."""
        csv_string = """name,nfc_tag,rfid_tag,email
Charlie,NFC003,RFID003,charlie@example.com"""
        
        parser = CSVRosterParser(strict_validation=False)
        roster_data = parser.parse_csv_string(csv_string)
        
        assert len(roster_data) == 1
        assert roster_data[0].nfc_id == "NFC003"
    
    def test_parse_csv_string_with_missing_required_column(self):
        """Test parsing CSV with missing required column raises error."""
        csv_string = """name,nfc_tag,email
Alice,NFC001,alice@example.com"""
        
        parser = CSVRosterParser(strict_validation=True)
        
        with pytest.raises(CSVInputError) as exc_info:
            parser.parse_csv_string(csv_string)
        
        assert "rfid_tag" in str(exc_info.value).lower()


@pytest.mark.external
class TestCSVParserValidation:
    """Test CSV validation functionality."""
    
    def test_validate_unique_tags_accepts_unique_tags(self):
        """Test that unique tags pass validation with real data."""
        parser = CSVRosterParser()
        roster_data = parser.parse_csv_file(str(ATHLETES_CSV))
        
        ok, errors = parser.validate_unique_tags(roster_data)
        
        assert ok is True
        assert len(errors) == 0
    
    def test_validate_unique_tags_detects_duplicate_nfc(self):
        """Test that duplicate NFC tags are detected."""
        roster_data = [
            RosterData(name="Alice", nfc_id="NFC001", rfid_id="RFID001"),
            RosterData(name="Bob", nfc_id="NFC001", rfid_id="RFID002"),  # Duplicate NFC
        ]
        
        parser = CSVRosterParser()
        ok, errors = parser.validate_unique_tags(roster_data)
        
        assert ok is False
        assert len(errors) > 0
        assert "NFC001" in str(errors)
    
    def test_validate_unique_tags_detects_duplicate_rfid(self):
        """Test that duplicate RFID tags are detected."""
        roster_data = [
            RosterData(name="Alice", nfc_id="NFC001", rfid_id="RFID001"),
            RosterData(name="Bob", nfc_id="NFC002", rfid_id="RFID001"),  # Duplicate RFID
        ]
        
        parser = CSVRosterParser()
        ok, errors = parser.validate_unique_tags(roster_data)
        
        assert ok is False
        assert any("RFID001" in error for error in errors)


@pytest.mark.external
class TestCSVParserStrictMode:
    """Test CSV parser strict validation mode."""
    
    def test_strict_mode_raises_on_invalid_row(self):
        """Test that strict mode raises on invalid rows."""
        csv_string = """name,nfc_tag,rfid_tag,email
Alice,NFC001,RFID001,alice@example.com
X,NFC002,RFID002,invalid"""  # Name too short
        
        parser = CSVRosterParser(strict_validation=True)
        
        with pytest.raises(CSVInputError):
            parser.parse_csv_string(csv_string)
    
    def test_non_strict_mode_skips_invalid_rows(self):
        """Test that non-strict mode skips invalid rows."""
        csv_string = """name,nfc_tag,rfid_tag,email
Alice,NFC001,RFID001,alice@example.com
X,NFC002,RFID002,invalid
Bob,NFC003,RFID003,bob@example.com"""
        
        parser = CSVRosterParser(strict_validation=False)
        roster_data = parser.parse_csv_string(csv_string)
        
        # Should parse Alice and Bob, skip X
        assert len(roster_data) == 2
        assert roster_data[0].name == "Alice"
        assert roster_data[1].name == "Bob"
