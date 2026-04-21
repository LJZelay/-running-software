import glob
class StorageThresholdWarning(Exception):
    pass
import os
import json
import pprint


def save_workout_summary(workout_id: str, summary: dict) -> None:
    index_path = os.path.join("data", "workouts", "index.json")
    workout_dir = os.path.join("data", "workouts", workout_id)
    summary_path = os.path.join(workout_dir, "summary.json")

    os.makedirs(workout_dir, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f)

    name = summary.get("name", "")
    date = summary.get("date", "")

    # Load existing index
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            try:
                index = json.load(f)
            except Exception:
                index = []
    else:
        index = []

    # Find if this workout_id already exists
    existing_entry = None
    for entry in index:
        if entry.get("workout_id") == workout_id:
            existing_entry = entry
            break

    if existing_entry:
        # UPDATE the existing entry with new name and date
        existing_entry["name"] = name
        existing_entry["date"] = date
    else:
        # ADD new entry
        index.append({"workout_id": workout_id, "name": name, "date": date})

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f)

    # Storage management
    workouts_dir = os.path.join("data", "workouts")
    max_storage_mb = 10
    warn_threshold_mb = 9
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(workouts_dir):
        for filename in filenames:
            fp = os.path.join(dirpath, filename)
            total_size += os.path.getsize(fp)
    total_mb = total_size / (1024 * 1024)
    if total_mb >= warn_threshold_mb:
        # Find all summary.json files except the current one
        summary_files = glob.glob(os.path.join(workouts_dir, "*", "summary.json"))
        # Exclude current workout
        summary_files = [f for f in summary_files if workout_id not in f]
        # Sort by mtime (oldest first)
        summary_files.sort(key=lambda x: os.path.getmtime(x))
        # Delete up to 3 oldest
        for old_file in summary_files[:3]:
            try:
                os.remove(old_file)
                # Remove parent dir if empty
                parent = os.path.dirname(old_file)
                if not os.listdir(parent):
                    os.rmdir(parent)
            except Exception:
                pass
        raise StorageThresholdWarning(f"Storage is near maximum ({total_mb:.2f} MB). Oldest 3 workout summaries deleted.")

def list_workouts() -> list[dict]:
    index_path = os.path.join("data", "workouts", "index.json")
    if not os.path.exists(index_path):
        return []
    with open(index_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def load_workout_summary(workout_id: str) -> dict:
    summary_path = os.path.join("data", "workouts", workout_id, "summary.json")
    if not os.path.exists(summary_path):
        return {}
    with open(summary_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def build_workout_summary(config, roster_file, event_data):
    """
    Build a complete workout summary dictionary.

    Args:
        config (dict): Workout configuration.
        roster_file (str): Path to the roster CSV file.
        event_data (dict): All event data for the workout.

    Returns:
        dict: Complete summary.
    """
    summary = {
        "config": config,
        "roster_file": roster_file,
        "results": {},
        "global_metrics": {},
        "graph_data": {}
    }

    results = {}
    pace_all = []
    interval_times_all = []
    pace_over_time = {}
    interval_times = {}

    for runner_id, runner_events in event_data.get("results", {}).items():
        intervals = runner_events.get("intervals", [])
        run_time = runner_events.get("run_time", 0)
        rest_time = runner_events.get("rest_time", 0)
        splits = runner_events.get("splits", [])
        pace = runner_events.get("pace", [])
        average_pace = sum(pace) / len(pace) if pace else 0

        results[runner_id] = {
            "intervals": intervals,
            "run_time": run_time,
            "rest_time": rest_time,
            "splits": splits,
            "pace": pace,
            "average_pace": average_pace
        }

        pace_all.append(average_pace)
        interval_times_all.extend(intervals)
        pace_over_time[runner_id] = pace
        interval_times[runner_id] = intervals

    # Global metrics
    fastest_runner = None
    slowest_runner = None
    if results:
        fastest_runner = min(results.items(), key=lambda x: x[1]["average_pace"])[0]
        slowest_runner = max(results.items(), key=lambda x: x[1]["average_pace"])[0]
    average_pace_all = sum(pace_all) / len(pace_all) if pace_all else 0

    summary["results"] = results
    summary["global_metrics"] = {
        "fastest_runner": fastest_runner,
        "slowest_runner": slowest_runner,
        "average_pace_all": average_pace_all
    }
    summary["graph_data"] = {
        "pace_over_time": pace_over_time,
        "interval_times": interval_times
    }


    return summary
