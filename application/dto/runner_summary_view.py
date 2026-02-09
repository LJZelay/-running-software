from typing import Optional #DTO for representing the summary information of a runner in the workout.


class RunnerSummaryView:
    
    def __init__(
        self,
        runner_id: int,
        runner_name: str,
        total_intervals_completed: int,
        average_pace: Optional[float] = None
    ):
        self.runner_id = runner_id
        self.runner_name = runner_name
        self.total_intervals_completed = total_intervals_completed
        self.average_pace = average_pace
