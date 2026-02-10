from application.exceptions import InvalidApplicationRequestError #Custom exception to indicate that a workout with the specified ID was not found in the repository.


def validate_positive_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or value <= 0:
        raise InvalidApplicationRequestError(f"{field_name} must be a positive integer")


def validate_non_empty_string(value: str, field_name: str) -> None:
    if not isinstance(value, str) or len(value.strip()) == 0:
        raise InvalidApplicationRequestError(f"{field_name} must be a non-empty string")
