import tkinter as tk
from tkinter import ttk
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from application.dto.runner_analytics_dto import RunnerAnalyticsDTO
from gui.analytics_widgets import plot_pace_trend_for_single
from gui.theme import ModernTheme


class RunnerView(tk.Toplevel):
    """Runner personal view with stats and controls."""

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
        self.get_rest_uc = get_rest_uc
        self.get_runner_analytics_uc = get_runner_analytics_uc
        self.scan_nfc_uc = scan_nfc_uc
        self.scan_rfid_uc = scan_rfid_uc
        self.runner_id = runner_id
        self.workout_id = workout_id
        self.refresh_interval_ms = refresh_interval_ms
        self.lap_count = 0

        self.title("Runner Dashboard")
        self.geometry("700x600")
        ModernTheme.configure(self)
        self._setup_ui()
        self._start_polling()

    def _setup_ui(self):
        ttk.Label(self, text="Runner Dashboard", style="Title.TLabel").pack(side=tk.TOP, padx=16, pady=(12, 6))

        btn_frame = ttk.Frame(self, style="Toolbar.TFrame", padding=(16, 6))
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="🏃 Simulate Lap", command=self._simulate_lap, style="Success.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="📞 Request Coach", command=self._request_coach).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="🔄 Refresh", command=self._refresh).pack(side=tk.LEFT, padx=4)

        self.main = ttk.Frame(self, padding=16)
        self.main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.main, text="Status", style="Header.TLabel").pack(anchor=tk.W)
        self.status = ttk.Label(self.main, text="Ready", style="Status.TLabel")
        self.status.pack(anchor=tk.W, pady=(4, 8))

        ttk.Label(self.main, text="Rest Timer", style="Header.TLabel").pack(anchor=tk.W)
        self.timer = ttk.Label(self.main, text="-- s", style="Status.TLabel")
        self.timer.pack(anchor=tk.W, pady=(4, 8))

        ttk.Label(self.main, text="Laps Today", style="Header.TLabel").pack(anchor=tk.W)
        self.lap_label = ttk.Label(self.main, text=f"Laps: {self.lap_count}", style="Status.TLabel")
        self.lap_label.pack(anchor=tk.W, pady=(4, 12))

        self.feedback = ttk.Label(self.main, text="Ready for action", wraplength=400)
        self.feedback.pack(anchor=tk.W, pady=10)

        self.chart_frame = ttk.Frame(self.main)
        self.chart_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.fig = None
        self.canvas = None

    def _start_polling(self):
        self._poll()
        self.after(self.refresh_interval_ms, self._start_polling)

    def _poll(self):
        try:
            rest_views = self.get_rest_uc.execute(self.workout_id)
            my_rest = next((v for v in rest_views if v.runner_id == self.runner_id), None)
            if my_rest:
                self.timer.config(text=f"{my_rest.remaining_rest_seconds} s")
                self.status.config(text=f"Resting - {"Ready!" if my_rest.is_ready_to_run else "Wait..."}")
            else:
                self.status.config(text="Running")
        except:
            pass

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
                    self.fig.clear()
                    self.fig = plot_pace_trend_for_single(my_analytics, fig=self.fig)
                    self.canvas.draw()
        except:
            pass

    def _simulate_lap(self):
        self.lap_count += 1
        self.lap_label.config(text=f"Laps: {self.lap_count}")
        self.feedback.config(text=f"✓ Lap {self.lap_count} recorded at {datetime.now().strftime('%H:%M:%S')}")

    def _request_coach(self):
        self.feedback.config(text="📞 Request sent to coach - awaiting response...")

    def _refresh(self):
        self._poll()
        self.feedback.config(text="✓ Data refreshed")
