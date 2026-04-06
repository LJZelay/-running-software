import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import List

from application.dto.runner_rest_view import RunnerRestView
from application.dto.runner_running_view import RunnerRunningView
from application.dto.runner_analytics_dto import RunnerAnalyticsDTO
from application.dto.workout_stats_dto import WorkoutStatsDTO
from gui.analytics_widgets import plot_pace_trend, plot_split_distribution
from gui.utils import PollingTimer


class CoachView(tk.Frame):
    """
    Coach GUI window displaying real-time workout data and analytics.
    """

    def __init__(
        self,
        parent,
        get_rest_uc,
        get_running_uc,
        get_runner_analytics_uc,
        get_workout_stats_uc,
        workout_id: int,
        refresh_interval_ms: int = 1000,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.get_rest_uc = get_rest_uc
        self.get_running_uc = get_running_uc
        self.get_runner_analytics_uc = get_runner_analytics_uc
        self.get_workout_stats_uc = get_workout_stats_uc
        self.workout_id = workout_id
        self.refresh_interval_ms = refresh_interval_ms

        self._setup_ui()
        self._start_polling()

    def _setup_ui(self):
        """Create the UI widgets."""
        self.parent.title("Coach View - Interval Workout Manager")

        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Live status
        self.live_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.live_frame, text="Live Status")

        # Sub-frames inside live_frame
        self.running_frame = ttk.LabelFrame(self.live_frame, text="Running Athletes")
        self.running_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.running_tree = ttk.Treeview(
            self.running_frame,
            columns=("name", "interval", "laps", "progress"),
            show="headings"
        )
        self.running_tree.heading("name", text="Name")
        self.running_tree.heading("interval", text="Interval")
        self.running_tree.heading("laps", text="Laps")
        self.running_tree.heading("progress", text="Progress")
        self.running_tree.pack(fill=tk.BOTH, expand=True)

        self.resting_frame = ttk.LabelFrame(self.live_frame, text="Resting Athletes")
        self.resting_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.resting_tree = ttk.Treeview(
            self.resting_frame,
            columns=("name", "remaining", "ready"),
            show="headings"
        )
        self.resting_tree.heading("name", text="Name")
        self.resting_tree.heading("remaining", text="Remaining Rest (s)")
        self.resting_tree.heading("ready", text="Ready")
        self.resting_tree.pack(fill=tk.BOTH, expand=True)

        # Tab 2: Analytics
        self.analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_frame, text="Analytics")

        # Analytics stats summary
        self.stats_frame = ttk.Frame(self.analytics_frame)
        self.stats_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        self.stats_label = ttk.Label(self.stats_frame, text="Workout stats not loaded yet.")
        self.stats_label.pack(anchor=tk.W)

        # Charts container (can be multiple)
        self.chart_frame = ttk.Frame(self.analytics_frame)
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Placeholder for figures and canvases
        self.figures = []
        self.canvas_widgets = []

    def _start_polling(self):
        """Start periodic updates."""
        self._poll()
        self.after(self.refresh_interval_ms, self._start_polling)

    def _poll(self):
        """Fetch latest data and update UI."""
        # Update running and resting tables
        try:
            running_views = self.get_running_uc.execute(self.workout_id)
            self._update_running_table(running_views)
        except Exception as e:
            print(f"Error fetching running data: {e}")

        try:
            resting_views = self.get_rest_uc.execute(self.workout_id)
            self._update_resting_table(resting_views)
        except Exception as e:
            print(f"Error fetching resting data: {e}")

        # Update analytics charts (less frequently maybe)
        self._update_analytics()

    def _update_running_table(self, running_views: List[RunnerRunningView]):
        """Update the treeview for running athletes."""
        self.running_tree.delete(*self.running_tree.get_children())
        for view in running_views:
            progress = f"{view.laps_completed}/{view.laps_per_interval} laps"
            self.running_tree.insert("", tk.END, values=(
                view.runner_name,
                view.interval_number,
                f"{view.laps_completed}",
                progress
            ))

    def _update_resting_table(self, resting_views: List[RunnerRestView]):
        """Update the treeview for resting athletes."""
        self.resting_tree.delete(*self.resting_tree.get_children())
        for view in resting_views:
            self.resting_tree.insert("", tk.END, values=(
                view.runner_name,
                view.remaining_rest_seconds,
                "Yes" if view.is_ready_to_run else "No"
            ))

    def _clear_charts(self):
        """Destroy all chart widgets and close prior figures before redrawing."""
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        for fig in self.figures:
            try:
                plt.close(fig)
            except Exception:
                pass
        self.figures.clear()
        self.canvas_widgets.clear()

    def _format_workout_stats(self, workout_stats: WorkoutStatsDTO) -> str:
        """Create a short summary string for workout statistics."""
        average_pace = workout_stats.average_pace_per_interval
        interval_summary = ", ".join(
            f"{interval}: {pace:.1f}s/km"
            for interval, pace in sorted(average_pace.items())
        ) if average_pace else "No intervals completed yet"
        return (
            f"Total runners: {workout_stats.total_runners} | "
            f"Intervals completed: {workout_stats.intervals_completed} | "
            f"Average pace: {interval_summary}"
        )

    def _update_analytics(self):
        """Update charts with fresh analytics data."""
        try:
            runner_analytics = self.get_runner_analytics_uc.execute(self.workout_id)
            workout_stats = self.get_workout_stats_uc.execute(self.workout_id)
        except Exception as e:
            print(f"Error fetching analytics: {e}")
            return

        self._clear_charts()
        self.stats_label.config(text=self._format_workout_stats(workout_stats))

        # Create a new figure for pace trends
        pace_fig = plot_pace_trend(runner_analytics)
        canvas = FigureCanvasTkAgg(pace_fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.figures.append(pace_fig)
        self.canvas_widgets.append(canvas)

        # Optionally add more charts
        # ...