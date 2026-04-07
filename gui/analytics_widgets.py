import matplotlib.pyplot as plt
from typing import List, Optional

from application.dto.runner_analytics_dto import RunnerAnalyticsDTO


def _format_seconds(seconds: float) -> str:
    """Format pace/interval values as MM:SS."""
    if seconds is None or seconds <= 0:
        return "--"

    minutes = int(seconds) // 60
    secs = int(round(seconds - minutes * 60))
    return f"{minutes}:{secs:02d}"


def plot_pace_trend(runner_analytics: List[RunnerAnalyticsDTO]) -> plt.Figure:
    """Create a line chart showing pace trends for all runners."""
    fig, ax = plt.subplots(figsize=(7, 4))

    if not runner_analytics:
        ax.text(0.5, 0.5, "No analytics data available", ha="center", va="center")
        ax.set_axis_off()
        fig.tight_layout()
        return fig

    plotted = False
    for analytics in runner_analytics:
        interval_numbers = [interval.interval_number for interval in analytics.intervals]
        paces = [interval.pace_per_km for interval in analytics.intervals]
        if interval_numbers and paces:
            ax.plot(interval_numbers, paces, marker="o", label=analytics.runner_name)
            plotted = True

    ax.set_title("Runner Pace Trend")
    ax.set_xlabel("Interval")
    ax.set_ylabel("Pace (s per km)")
    ax.grid(True, linestyle="--", alpha=0.4)
    if plotted:
        ax.legend(loc="best", fontsize="small")
    fig.tight_layout()
    return fig


def plot_split_distribution(runner_analytics: List[RunnerAnalyticsDTO]) -> plt.Figure:
    """Create a histogram of split times across runners."""
    fig, ax = plt.subplots(figsize=(7, 4))
    split_values = []
    for analytics in runner_analytics:
        for interval in analytics.intervals:
            split_values.extend([split / 1000.0 for split in interval.splits_ms])

    if not split_values:
        ax.text(0.5, 0.5, "No split time data available", ha="center", va="center")
        ax.set_axis_off()
        fig.tight_layout()
        return fig

    ax.hist(split_values, bins=min(10, max(1, len(split_values))), edgecolor="black", alpha=0.7)
    ax.set_title("Split Time Distribution")
    ax.set_xlabel("Split time (seconds)")
    ax.set_ylabel("Frequency")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig


def plot_pace_trend_for_single(analytics: RunnerAnalyticsDTO, fig: Optional[plt.Figure] = None) -> plt.Figure:
    """Create or update a pace trend chart for a single runner."""
    if fig is None:
        fig, ax = plt.subplots(figsize=(6, 3.5))
    else:
        fig.clf()
        ax = fig.add_subplot(111)

    if not analytics or not analytics.intervals:
        ax.text(0.5, 0.5, "No pace data available", ha="center", va="center")
        ax.set_axis_off()
        fig.tight_layout()
        return fig

    interval_numbers = [interval.interval_number for interval in analytics.intervals]
    paces = [interval.pace_per_km for interval in analytics.intervals]

    ax.plot(interval_numbers, paces, marker="o", linestyle="-", color="#007acc")
    ax.set_title(f"{analytics.runner_name} Pace Trend")
    ax.set_xlabel("Interval")
    ax.set_ylabel("Pace (s per km)")
    ax.set_xticks(interval_numbers)
    ax.grid(True, linestyle="--", alpha=0.4)

    average_pace_text = _format_seconds(analytics.overall_avg_pace)
    ax.text(0.95, 0.02, f"Avg pace: {average_pace_text}", transform=ax.transAxes,
            ha="right", va="bottom", fontsize="small", color="#444444")

    fig.tight_layout()
    return fig


def plot_run_vs_rest_time(runner_analytics: List[RunnerAnalyticsDTO]) -> plt.Figure:
    """Create a bar chart comparing total run time vs rest time for all runners."""
    fig, ax = plt.subplots(figsize=(7, 4))
    
    if not runner_analytics:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center")
        ax.set_axis_off()
        fig.tight_layout()
        return fig
    
    runner_names = []
    run_times = []
    rest_times = []
    
    for analytics in runner_analytics:
        # Calculate total run time from intervals
        total_run = sum(interval.race_time_s for interval in analytics.intervals if interval.race_time_s)
        # Calculate total rest time
        total_rest = sum(interval.rest_time_s for interval in analytics.intervals if interval.rest_time_s)
        
        runner_names.append(analytics.runner_name)
        run_times.append(total_run)
        rest_times.append(total_rest)
    
    x = range(len(runner_names))
    width = 0.35
    
    ax.bar([i - width/2 for i in x], run_times, width, label="Run Time", color="#007AFF")
    ax.bar([i + width/2 for i in x], rest_times, width, label="Rest Time", color="#34C759")
    
    ax.set_xlabel("Runner")
    ax.set_ylabel("Time (seconds)")
    ax.set_title("Run Time vs Rest Time by Runner")
    ax.set_xticks(x)
    ax.set_xticklabels(runner_names, rotation=45, ha="right")
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    
    fig.tight_layout()
    return fig


def plot_rest_efficiency(runner_analytics: List[RunnerAnalyticsDTO]) -> plt.Figure:
    """Create a chart showing rest efficiency (heart rate recovery proxy)."""
    fig, ax = plt.subplots(figsize=(7, 4))
    
    if not runner_analytics:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center")
        ax.set_axis_off()
        fig.tight_layout()
        return fig
    
    runner_names = []
    efficiency_scores = []
    
    for analytics in runner_analytics:
        runner_names.append(analytics.runner_name)
        # Efficiency = average rest time / number of intervals (more rest per interval = better recovery)
        total_intervals = len(analytics.intervals)
        if total_intervals > 0:
            avg_rest = sum(interval.rest_time_s for interval in analytics.intervals if interval.rest_time_s) / total_intervals
            efficiency_scores.append(avg_rest)
        else:
            efficiency_scores.append(0)
    
    colors = ["#34C759" if score >= 45 else "#FF9500" if score >= 30 else "#FF3B30" for score in efficiency_scores]
    ax.bar(runner_names, efficiency_scores, color=colors)
    
    ax.set_ylabel("Average Rest Time per Interval (seconds)")
    ax.set_title("Rest Efficiency by Runner")
    ax.axhline(y=45, color="green", linestyle="--", alpha=0.5, label="Good (45s)")
    ax.axhline(y=30, color="orange", linestyle="--", alpha=0.5, label="Adequate (30s)")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    ax.legend(fontsize="small")
    
    fig.tight_layout()
    return fig


def plot_average_pace_by_runner(runner_analytics: List[RunnerAnalyticsDTO]) -> plt.Figure:
    """Create a bar chart showing average pace for each runner."""
    fig, ax = plt.subplots(figsize=(7, 4))
    
    if not runner_analytics:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center")
        ax.set_axis_off()
        fig.tight_layout()
        return fig
    
    runner_names = [analytics.runner_name for analytics in runner_analytics]
    avg_paces = [analytics.overall_avg_pace for analytics in runner_analytics if analytics.overall_avg_pace]
    
    if not avg_paces:
        ax.text(0.5, 0.5, "No pace data available", ha="center", va="center")
        ax.set_axis_off()
        fig.tight_layout()
        return fig
    
    # Color code by pace performance (faster = more blue, slower = more orange)
    min_pace = min(avg_paces)
    max_pace = max(avg_paces)
    pace_range = max_pace - min_pace if max_pace > min_pace else 1
    
    colors = []
    for pace in avg_paces:
        normalized = (pace - min_pace) / pace_range if pace_range > 0 else 0
        if normalized < 0.33:
            colors.append("#34C759")  # Green - fast
        elif normalized < 0.67:
            colors.append("#007AFF")  # Blue - medium
        else:
            colors.append("#FF9500")  # Orange - slower
    
    bars = ax.bar(runner_names[:len(avg_paces)], avg_paces, color=colors)
    
    # Add pace labels on bars
    for bar, pace in zip(bars, avg_paces):
        height = bar.get_height()
        pace_text = _format_seconds(pace)
        ax.text(bar.get_x() + bar.get_width()/2., height,
                pace_text, ha='center', va='bottom', fontsize='small')
    
    ax.set_ylabel("Average Pace (s per km)")
    ax.set_title("Average Pace by Runner")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    
    fig.tight_layout()
    return fig


def plot_workout_progress(runner_analytics: List[RunnerAnalyticsDTO]) -> plt.Figure:
    """Create a stacked bar chart showing workout progress for each runner."""
    fig, ax = plt.subplots(figsize=(7, 4))
    
    if not runner_analytics:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center")
        ax.set_axis_off()
        fig.tight_layout()
        return fig
    
    runner_names = []
    completed_intervals = []
    total_intervals_list = []
    
    for analytics in runner_analytics:
        runner_names.append(analytics.runner_name)
        completed = len([i for i in analytics.intervals if i.race_time_s and i.race_time_s > 0])
        total_intervals = len(analytics.intervals)
        completed_intervals.append(completed)
        total_intervals_list.append(total_intervals)
    
    if not total_intervals_list or sum(total_intervals_list) == 0:
        ax.text(0.5, 0.5, "No interval data available", ha="center", va="center")
        ax.set_axis_off()
        fig.tight_layout()
        return fig
    
    x = range(len(runner_names))
    width = 0.6
    
    ax.bar(x, completed_intervals, width, label="Completed", color="#007AFF")
    remaining = [total - completed for total, completed in zip(total_intervals_list, completed_intervals)]
    ax.bar(x, remaining, width, bottom=completed_intervals, label="Remaining", color="#C4C4C6")
    
    # Add percentage labels
    for i, (runner, total, completed) in enumerate(zip(runner_names, total_intervals_list, completed_intervals)):
        percentage = (completed / total * 100) if total > 0 else 0
        ax.text(i, total + 0.5, f"{percentage:.0f}%", ha="center", va="bottom", fontsize="small", fontweight="bold")
    
    ax.set_xlabel("Runner")
    ax.set_ylabel("Intervals")
    ax.set_title("Workout Progress")
    ax.set_xticks(x)
    ax.set_xticklabels(runner_names)
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    
    fig.tight_layout()
    return fig
