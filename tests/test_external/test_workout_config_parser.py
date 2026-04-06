import pytest

from externalInterface.csv_workout_config_parser import CSVWorkoutConfigParser
from externalInterface.csv_roster_parser import CSVInputError


class TestCSVWorkoutConfigParser:
    def test_parse_valid_workout_config(self):
        csv_string = """intervalDistance,lapsPerInterval,startMode,workout_id
400,3,INDIVIDUAL,1"""
        parser = CSVWorkoutConfigParser()
        config = parser.parse_csv_string(csv_string)

        assert config.interval_distance == 400
        assert config.laps_per_interval == 3
        assert config.start_mode == "INDIVIDUAL"
        assert config.workout_id == 1

    def test_parse_default_start_mode(self):
        csv_string = """intervalDistance,lapsPerInterval
500,2"""
        parser = CSVWorkoutConfigParser()
        config = parser.parse_csv_string(csv_string)

        assert config.interval_distance == 500
        assert config.laps_per_interval == 2
        assert config.start_mode == "INDIVIDUAL"

    def test_parse_missing_required_field_raises(self):
        csv_string = """intervalDistance,startMode
400,INDIVIDUAL"""
        parser = CSVWorkoutConfigParser()

        with pytest.raises(CSVInputError):
            parser.parse_csv_string(csv_string)
