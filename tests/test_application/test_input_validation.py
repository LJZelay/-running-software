"""Unit tests for input validation functions."""
import pytest
from application.input_validation import validate_positive_int, validate_non_empty_string
from application.exceptions import InvalidApplicationRequestError


@pytest.mark.application
class TestValidatePositiveInt:
    """Test positive integer validation."""
    
    def test_validate_positive_int_accepts_valid_positive_integer(self):
        """Test that positive integers pass validation."""
        # Should not raise
        validate_positive_int(1, "test_field")
        validate_positive_int(100, "test_field")
        validate_positive_int(999999, "test_field")
    
    def test_validate_positive_int_rejects_zero(self):
        """Test that zero is rejected."""
        with pytest.raises(InvalidApplicationRequestError):
            validate_positive_int(0, "workout_id")
    
    def test_validate_positive_int_rejects_negative(self):
        """Test that negative numbers are rejected."""
        with pytest.raises(InvalidApplicationRequestError):
            validate_positive_int(-1, "runner_id")
        
        with pytest.raises(InvalidApplicationRequestError):
            validate_positive_int(-100, "interval_distance")
    
    def test_validate_positive_int_rejects_non_integer(self):
        """Test that non-integer types are rejected."""
        with pytest.raises(InvalidApplicationRequestError):
            validate_positive_int("1", "workout_id")
        
        with pytest.raises(InvalidApplicationRequestError):
            validate_positive_int(1.5, "runner_id")
        
        with pytest.raises(InvalidApplicationRequestError):
            validate_positive_int(None, "test_field")


@pytest.mark.application
class TestValidateNonEmptyString:
    """Test non-empty string validation."""
    
    def test_validate_non_empty_string_accepts_valid_strings(self):
        """Test that non-empty strings pass validation."""
        # Should not raise
        validate_non_empty_string("NFC001", "nfc_tag")
        validate_non_empty_string("Alice Smith", "runner_name")
        validate_non_empty_string("path/to/file.csv", "file_path")
    
    def test_validate_non_empty_string_rejects_empty_string(self):
        """Test that empty strings are rejected."""
        with pytest.raises(InvalidApplicationRequestError):
            validate_non_empty_string("", "nfc_tag")
    
    def test_validate_non_empty_string_rejects_whitespace_only(self):
        """Test that whitespace-only strings are rejected."""
        with pytest.raises(InvalidApplicationRequestError):
            validate_non_empty_string("   ", "tag_id")
        
        with pytest.raises(InvalidApplicationRequestError):
            validate_non_empty_string("\t\n", "runner_name")
    
    def test_validate_non_empty_string_rejects_non_string_types(self):
        """Test that non-string types are rejected."""
        with pytest.raises(InvalidApplicationRequestError):
            validate_non_empty_string(123, "nfc_tag")
        
        with pytest.raises(InvalidApplicationRequestError):
            validate_non_empty_string(None, "runner_name")
        
        with pytest.raises(InvalidApplicationRequestError):
            validate_non_empty_string(["NFC001"], "tag_list")
