from pathlib import Path
from typing import List, Protocol


class RunnerReportGenerator(Protocol):
    def generate_reports_for_workout(self, workout: object, output_dir: Path) -> List[Path]:
        ...


class GenerateRunnerReportUseCase:
    """Application use case that delegates runner report generation to an output adapter."""

    def __init__(self, report_generator: RunnerReportGenerator) -> None:
        self.report_generator = report_generator

    def execute(self, workout: object, output_dir: Path) -> List[Path]:
        return self.report_generator.generate_reports_for_workout(workout, output_dir=output_dir)
