class WorkoutStatusView: #DTO for representing the status of a workout, including the workout state and the count of active and resting runners.
    
    def __init__(
        self,
        workout_id: int,
        workout_state: str,
        active_runner_count: int,
        resting_runner_count: int
    ):
        self.workout_id = workout_id
        self.workout_state = workout_state
        self.active_runner_count = active_runner_count
        self.resting_runner_count = resting_runner_count
