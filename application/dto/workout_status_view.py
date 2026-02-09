class WorkoutStatusView:
    
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
