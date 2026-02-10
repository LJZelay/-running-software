class WorkoutNotFoundError(Exception): #Custom exception to indicate that a workout with the specified ID was not found in the repository.
    pass


class InvalidApplicationRequestError(Exception):
    pass
