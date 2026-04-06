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
