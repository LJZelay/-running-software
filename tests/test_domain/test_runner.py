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


@pytest.mark.domain
class TestRunnerSerialization:
    """Test Runner serialization and deserialization."""
    
    def test_runner_to_dict_conversion(self):
        """Test that runner converts to dictionary correctly."""
        runner = load_athlete_from_csv(0)  # Load Alice
        runner_dict = runner.to_dict()
        
        assert runner_dict["name"] == "Alice"
        assert runner_dict["nfc_tag"] == "NFC001"
        assert runner_dict["rfid_tag"] == "RFID001"
    
    def test_runner_from_dict_conversion(self):
        """Test that runner can be created from dictionary."""
        original = load_athlete_from_csv(1)  # Load Bob
        data = original.to_dict()
        
        runner = Runner.from_dict(data)
        
        assert runner.name == original.name
        assert runner.nfc_tag == original.nfc_tag
        assert runner.rfid_tag == original.rfid_tag
    
    def test_runner_roundtrip_conversion(self):
        """Test that runner survives roundtrip to dict and back."""
        original = load_athlete_from_csv(2)  # Load Charlie
        
        reconstructed = Runner.from_dict(original.to_dict())
        
        assert original.name == reconstructed.name
        assert original.nfc_tag == reconstructed.nfc_tag
        assert original.rfid_tag == reconstructed.rfid_tag