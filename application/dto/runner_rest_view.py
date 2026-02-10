class RunnerRestView:
    
    def __init__(
        self,
        runner_id: int,
        runner_name: str,
        remaining_rest_seconds: int,
        is_ready_to_run: bool
    ):
        self.runner_id = runner_id
        self.runner_name = runner_name
        self.remaining_rest_seconds = remaining_rest_seconds
        self.is_ready_to_run = is_ready_to_run
