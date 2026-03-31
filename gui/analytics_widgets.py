import matplotlib.pyplot as plt
from typing import List
from application.dto.runner_analytics_dto import IntervalDetail, RunnerAnalyticsDTO


def plot_pace_trend(runner_analytics: List[RunnerAnalyticsDTO], figsize=(8, 5)):
    fig, ax = plt.subplots(figsize=figsize)
    has_data = False
    for ra in runner_analytics:
        intervals = [i.interval_number for i in ra.intervals]
        paces = [i.pace_per_km for i in ra.intervals]
        if intervals:
            ax.plot(intervals, paces, marker='o', label=ra.runner_name)
            has_data = True
    if has_data:
        ax.legend()
    ax.set_xlabel('Interval Number')
    ax.set_ylabel('Pace (sec/km)')
    ax.grid(True)
    fig.tight_layout()
    return fig


def plot_pace_trend_for_single(runner_analytics: RunnerAnalyticsDTO, fig=None):
    """
    Plot pace trend for a single runner.
    """
    if fig is None:
        fig, ax = plt.subplots(figsize=(6, 4))
    else:
        ax = fig.gca()
        ax.clear()

    intervals = [i.interval_number for i in runner_analytics.intervals]
    paces = [i.pace_per_km for i in runner_analytics.intervals]
    if intervals:
        ax.plot(intervals, paces, marker='o', color='blue')
    ax.set_xlabel('Interval Number')
    ax.set_ylabel('Pace (sec/km)')
    ax.set_title(f"Pace Trend - {runner_analytics.runner_name}")
    ax.grid(True)
    fig.tight_layout()
    return fig


def plot_split_distribution(interval: IntervalDetail, figsize=(6,4)):
    """
    Plot a histogram of split times for a specific interval.
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.hist(interval.splits_ms, bins=10, alpha=0.7, edgecolor='black')
    ax.set_xlabel('Split Time (ms)')
    ax.set_ylabel('Frequency')
    ax.set_title(f'Interval {interval.interval_number} Split Distribution')
    fig.tight_layout()
    return fig