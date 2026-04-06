import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import List

from application.dto.runner_rest_view import RunnerRestView
from application.dto.runner_analytics_dto import RunnerAnalyticsDTO
from gui.analytics_widgets import plot_pace_trend_for_single
from gui.utils import show_info_dialog


class RunnerView(tk.Toplevel):
    """
    Runner-specific view showing personal rest timer and pace trend.
    """

    def __init__(
        self,
        parent,
        get_rest_uc,
        get_runner_analytics_uc,
        runner_id: int,
        workout_id: int,
        scan_nfc_uc=None,
        scan_rfid_uc=None,
        refresh_interval_ms: int = 1000,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.get_rest_uc = get_rest_uc
        self.get_runner_analytics_uc = get_runner_analytics_uc
        self.scan_nfc_uc = scan_nfc_uc
        self.scan_rfid_uc = scan_rfid_uc
        self.runner_id = runner_id
        self.workout_id = workout_id
        self.refresh_interval_ms = refresh_interval_ms

        self.title("Runner View")
        self._setup_ui()
        self._start_polling()

    def _setup_ui(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("vista")
        except tk.TclError:
            pass
        self.style.configure("Header.TLabel", font=("Helvetica", 16, "bold"))
        self.style.configure("SubHeader.TLabel", font=("Helvetica", 11, "bold"))
        self.style.configure("Action.TButton", padding=6)

        self.main_frame = ttk.Frame(self, padding=12)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.title_label = ttk.Label(self.main_frame, text="Runner Dashboard", style="Header.TLabel")
        self.title_label.pack(anchor=tk.W, pady=(0, 8))

        button_bar = ttk.Frame(self.main_frame)
        button_bar.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(button_bar, text="Refresh", command=self._refresh_view, style="Action.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(button_bar, text="Simulate Lap", command=self._on_simulate_lap, style="Action.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(button_bar, text="Request Coach", command=self._on_request_coach, style="Action.TButton").pack(side=tk.LEFT, padx=4)

        self.status_label = ttk.Label(self.main_frame, text="Status: --", style="SubHeader.TLabel")
        self.status_label.pack(anchor=tk.W, pady=(0, 4))

        self.timer_label = ttk.Label(self.main_frame, text="Rest remaining: --")
        self.timer_label.pack(anchor=tk.W, pady=(0, 4))

        self.ready_label = ttk.Label(self.main_frame, text="Ready to run: --")
        self.ready_label.pack(anchor=tk.W, pady=(0, 10))

        self.feedback_label = ttk.Label(self.main_frame, text="Coach feedback will appear here.", wraplength=300)
        self.feedback_label.pack(fill=tk.X, pady=(0, 10))

        self.chart_frame = ttk.Frame(self.main_frame)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

        self.fig = None
        self.canvas = None

    def _start_polling(self):
        self._poll()
        self.after(self.refresh_interval_ms, self._start_polling)

    def _poll(self):
        # Fetch rest data (assuming we can filter by runner)
        resting_views = self.get_rest_uc.execute(self.workout_id)
        my_rest = next((v for v in resting_views if v.runner_id == self.runner_id), None)

        if my_rest:
            self.timer_label.config(text=f"Rest remaining: {my_rest.remaining_rest_seconds} s")
            self.ready_label.config(text=f"Ready to run: {'Yes' if my_rest.is_ready_to_run else 'No'}")
            self.status_label.config(text="Resting")
        else:
            # Check if runner is running (maybe via get_running_uc, but we don't have it here)
            # For simplicity, we'll just indicate no rest data
            self.status_label.config(text="Running or not started")

        # Fetch analytics and update pace trend chart
        try:
            analytics = self.get_runner_analytics_uc.execute(self.workout_id)
            my_analytics = next((a for a in analytics if a.runner_id == self.runner_id), None)
            if my_analytics:
                if self.fig is None:
                    self.fig = plot_pace_trend_for_single(my_analytics)
                    self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
                    self.canvas.draw()
                    self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                else:
                    # Update existing figure
                    self.fig.clear()
                    self.fig = plot_pace_trend_for_single(my_analytics, fig=self.fig)
                    self.canvas.draw()
        except Exception as e:
            print(f"Error updating runner view: {e}")

    def _refresh_view(self):
        self._poll()
        self._update_feedback("Data refreshed for your session.")

    def _on_simulate_lap(self):
        self._update_feedback("Simulated lap recorded. Your coach can review the update.")

    def _on_request_coach(self):
        show_info_dialog("Coach Request", "A request has been sent to your coach. Response will appear here.")
        self._update_feedback("Coach request sent.")

    def _update_feedback(self, message: str):
        self.feedback_label.config(text=message)