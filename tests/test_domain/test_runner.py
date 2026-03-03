"""Unit tests for the Runner domain entity."""
import pytest
import csv
from pathlib import Path
from domain.runner import Runner


# Path to actual test data
DATA_DIR = Path(__file__).parent.parent.parent / "data"
ATHLETES_CSV = DATA_DIR / "athletes.csv"


def load_athlete_from_csv(index: int = 0) -> Runner:
    """Load a single athlete from CSV file by index."""
    with open(ATHLETES_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if idx == index:
                return Runner(
                    runner_id=idx + 1,
                    name=row['name'],
                    email=row['email'],
                    nfc_tag=row['nfc_tag'],
                    rfid_tag=row['rfid_tag']
                )
    raise ValueError(f"Athlete at index {index} not found")


@pytest.mark.domain
class TestRunnerCreation:
    """Test Runner entity creation and validation."""
    
    def test_runner_creation_with_valid_data(self):
        """Test that a runner can be created with valid data from CSV."""
        runner = load_athlete_from_csv(0)  # Load Alice
        
        assert runner.id == 1
        assert runner.name == "Alice"
        assert runner.email == "alice@example.com"
        assert runner.nfc_tag == "NFC001"
        assert runner.rfid_tag == "RFID001"
    
    def test_runner_creation_with_empty_email(self):
        """Test that a runner can be created with empty email."""
        runner = Runner(
            runner_id=2,
            name="Bob",
            email="",
            nfc_tag="NFC002",
            rfid_tag="RFID002"
        )
        
        assert runTestRunner",
            email="",
            nfc_tag="NFC999",
            rfid_tag="RFID999
class TestRunnerSerialization:
    """Test Runner serialization and deserialization."""
    
    def test_runner_to_dict_conversion(self):
        """Test that runner converts to dictionary correctly."""
        runner = load_athlete_from_csv(0)  # Load Alice
        
        runner_dict = runner.to_dict()
        
        assert runner_dict["id"] == runner.id
        assert runner_dict["name"] == runner.name
        assert runner_dict["email"] == runner.email
        assert runner_dict["nfc_tag"] == runner.nfc_tag
        assert runner_dict["rfid_tag"] == runner.rfid_tag
    
    def test_runner_from_dict_conversion(self):
        """Test that runner can be created from dictionary."""
        data = {
            "id": 1,
            "name": "Alice",
            "email": "alice@example.com",
            "nfc_tag": "NFC001",
            "rfid_tag": "RFID001"
        original_runner = load_athlete_from_csv(0)  # Load Alice
        data = original_runner.to_dict()
        
        runner = Runner.from_dict(data)
        
        assert runner.id == original_runner.id
        assert runner.name == original_runner.name
        assert runner.email == original_runner.email
        assert runner.nfc_tag == original_runner.nfc_tag
        assert runner.rfid_tag == original_runner.rfid_tag
            email="charlie@example.com",
            nfc_tag="NFC005",
            rfid_tag="RFID005"
        )
        
        reconstructed = Runner.from_dict(original.to_dict())
        
        assert original.id == reconstructed.id
        assert origload_athlete_from_csv(2)  # Load Charlie