from application.dto.workout_status_view import WorkoutStatusView #DTO for representing the status of a workout, including the workout state and the count of active and resting runners.


class WorkoutStatusMapper:
    
    @staticmethod
    def from_workout(workout: object) -> WorkoutStatusView:
        active_count, resting_count = workout.get_runner_counts()
        
        return WorkoutStatusView(
            workout_id=workout.workout_id,
            workout_state=workout.status.value,
            active_runner_count=active_count,
            resting_runner_count=resting_count
        )

