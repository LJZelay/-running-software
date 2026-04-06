import tkinter as tk
from tkinter import ttk, filedialog
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import List
from datetime import datetime
import csv

from application.dto.runner_rest_view import RunnerRestView
from application.dto.runner_running_view import RunnerRunningView
from application.dto.runner_analytics_dto import RunnerAnalyticsDTO
from application.dto.workout_stats_dto import WorkoutStatsDTO
from gui.analytics_widgets import plot_pace_trend, plot_split_distribution
from gui.theme import ModernTheme


class CoachView(tk.Frame):
    """Coach dashboard with life status and analytics."""

    def __init__(
        self,
        parent,
        get_rest_uc,
        get_running_uc,
        get_runner_analytics_uc,
        get_workout_stats_uc,
        workout_id: int,
        start_workout_uc=None,
        end_workout_uc=None,
        refresh_interval_ms: int = 1000,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.get_rest_uc = get_rest_uc
        self.get_running_uc = get_running_uc
        self.get_runner_analytics_uc = get_runner_analytics_uc
        self.get_workout_stats_uc = get_workout_stats_uc
        self.start_workout_uc = start_workout_uc
        self.end_workout_uc = end_workout_uc
        self.workout_id = workout_id
        self.refresh_interval_ms = refresh_interval_ms
        self.chart_mode = "pace"
        self.workout_active = False

        ModernTheme.configure(parent)
        self._setup_ui()
        self._start_polling()

    def _setup_ui(self):
        """Create the UI widgets."""
        self.parent.title("Coach Dashboard - Interval Workout Manager")
        self.parent.geometry("1200x800")

        toolbar = ttk.Frame(self, style="Toolbar.TFrame", padding=(16, 12))
        toolbar.pack(fill=tk.X, side=tk.TOP)

        ttk.Label(toolbar, text="Coach Dashboard", style="Title.TLabel").pack(side=tk.LEFT)
        
        self.status_badge = tk.Canvas(toolbar, width=150, height=30, bg=ModernTheme.BG_DARK, highlightthickness=0)
        self.status_badge.pack(side=tk.RIGHT)
        self._update_status_badge("Standby")

        action_frame = ttk.Frame(self, style="Toolbar.TFrame", padding=(16, 6))
        action_frame.pack(fill=tk.X)

        self.btn_start = ttk.Button(action_frame, text="▶ Start", command=self._on_start_workout, style="Success.TButton")
        self.btn_start.pack(side=tk.LEFT, padx=4)

        self.btn_end = ttk.Button(action_frame, text="⏹ End", command=self._on_end_workout, style="Danger.TButton", state=tk.DISABLED)
        self.btn_end.pack(side=tk.LEFT, padx=4)

        ttk.Button(action_frame, text="🔄 Refresh", command=self._on_refresh).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="📊 Charts", command=self._on_toggle_chart).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="💾 Export", command=self._on_export).pack(side=tk.LEFT, padx=4)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Live Status Tab
        self.live_frame = tk.Frame(self, bg=ModernTheme.BG_DARK)
        self.notebook.add(self.live_frame, text="🔴 Live")

        ttk.Label(self.live_frame, text="🏃 Running", style="Header.TLabel").pack(anchor=tk.W, padx=10, pady=(10, 4))
        self.running_tree = ttk.Treeview(self.live_frame, columns=("name", "int", "laps", "prog"), height=8, show="headings")
        self.running_tree.heading("name", text="Name")
        self.running_tree.heading("int", text="Interval")
        self.running_tree.heading("laps", text="Laps")
        self.running_tree.heading("prog", text="Progress")
        self.running_tree.column("name", width=150)
        self.running_tree.column("int", width=70)
        self.running_tree.column("laps", width=70)
        self.running_tree.column("prog", width=150)
        self.running_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        ttk.Label(self.live_frame, text="😴 Rest", style="Header.TLabel").pack(anchor=tk.W, padx=10, pady=(10, 4))
        self.resting_tree = ttk.Treeview(self.live_frame, columns=("name", "time", "rdy"), height=6, show="headings")
        self.resting_tree.heading("name", text="Name")
        self.resting_tree.heading("time", text="Time Left")
        self.resting_tree.heading("rdy", text="Ready")
        self.resting_tree.column("name", width=150)
        self.resting_tree.column("time", width=100)
        self.resting_tree.column("rdy", width=80)
        self.resting_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Analytics Tab
        self.analytics_frame = tk.Frame(self, bg=ModernTheme.BG_DARK)
        self.notebook.add(self.analytics_frame, text="📈 Analytics")

        ttk.Label(self.analytics_frame, text="Stats", style="Header.TLabel").pack(anchor=tk.W, padx=10, pady=(10, 4))
        self.stats_label = ttk.Label(self.analytics_frame, text="Loading...", style="Status.TLabel")
        self.stats_label.pack(anchor=tk.W, padx=10, pady=4)

        self.chart_frame = ttk.Frame(self.analytics_frame)
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.figures = []
        self.canvas_widgets = []

    def _update_status_badge(self, status: str, color: str = ModernTheme.WARNING):
        self.status_badge.delete("all")
        self.status_badge.create_oval(10, 10, 20, 20, fill=color, outline=color)
        self.status_badge.create_text(35, 15, text=status, fill=ModernTheme.TEXT_PRIMARY, font=("Helvetica", 9, "bold"), anchor="w")

    def _start_polling(self):
        self._poll()
        self.after(self.refresh_interval_ms, self._start_polling)

    def _poll(self):
        try:
            running = self.get_running_uc.execute(self.workout_id)
            self._update_running_table(running)
        except Exception as e:
            pass

        try:
            resting = self.get_rest_uc.execute(self.workout_id)
            self._update_resting_table(resting)
        except Exception as e:
            pass

        self._update_analytics()

    def _update_running_table(self, views: List[RunnerRunningView]):
        self.running_tree.delete(*self.running_tree.get_children())
        for v in views:
            self.running_tree.insert("", tk.END, values=(v.runner_name, v.interval_number, v.laps_completed, f"{v.laps_completed}/{v.laps_per_interval}"))

    def _update_resting_table(self, views: List[RunnerRestView]):
        self.resting_tree.delete(*self.resting_tree.get_children())
        for v in views:
            self.resting_tree.insert("", tk.END, values=(v.runner_name, v.remaining_rest_seconds, "✓" if v.is_ready_to_run else "✗"))

    def _clear_charts(self):
        for w in self.chart_frame.winfo_children():
            w.destroy()
        for f in self.figures:
            try:
                plt.close(f)
            except:
                pass
        self.figures.clear()
        self.canvas_widgets.clear()

    def _on_refresh(self):
        self._poll()
        self._update_status_badge("✓", ModernTheme.SUCCESS)
        self.after(800, lambda: self._update_status_badge("Active ●" if self.workout_active else "Standby", ModernTheme.SUCCESS if self.workout_active else ModernTheme.WARNING))

    def _on_toggle_chart(self):
        self.chart_mode = "split" if self.chart_mode == "pace" else "pace"
        self._update_analytics()

    def _on_start_workout(self):
        try:
            if self.start_workout_uc:
                self.start_workout_uc.execute(self.workout_id)
                self.workout_active = True
                self.btn_start.config(state=tk.DISABLED)
                self.btn_end.config(state=tk.NORMAL)
                self._update_status_badge("▶ Active", ModernTheme.SUCCESS)
        except Exception as e:
            self._update_status_badge("Error", ModernTheme.DANGER)

    def _on_end_workout(self):
        try:
            if self.end_workout_uc:
                self.end_workout_uc.execute(self.workout_id)
                self.workout_active = False
                self.btn_start.config(state=tk.NORMAL)
                self.btn_end.config(state=tk.DISABLED)
                self._update_status_badge("⏹ Ended", ModernTheme.DANGER)
        except Exception as e:
            self._update_status_badge("Error", ModernTheme.DANGER)

    def _on_export(self):
        try:
            stats = self.get_workout_stats_uc.execute(self.workout_id)
            analytics = self.get_runner_analytics_uc.execute(self.workout_id)

            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if not path:
                return

            with open(path, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(["Workout Summary"])
                w.writerow(["Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                w.writerow([])
                w.writerow(["Total Runners", stats.total_runners])
                w.writerow(["Intervals", stats.intervals_completed])
                w.writerow([])
                w.writerow(["Runner", "Avg Pace", "Eff", "Count"])
                for a in analytics:
                    w.writerow([a.runner_name, f"{a.overall_avg_pace:.2f}", f"{(a.rest_efficiency*100 if a.rest_efficiency else 0):.0f}%", len(a.intervals)])

            self._update_status_badge("✓ Export", ModernTheme.SUCCESS)
        except:
            self._update_status_badge("Export fail", ModernTheme.DANGER)

    def _update_analytics(self):
        try:
            analytics = self.get_runner_analytics_uc.execute(self.workout_id)
            stats = self.get_workout_stats_uc.execute(self.workout_id)
        except:
            return

        self._clear_charts()
        self.stats_label.config(text=f"Runners: {stats.total_runners} | Intervals: {stats.intervals_completed}")

        if not analytics:
            ttk.Label(self.chart_frame, text="No data", style="Status.TLabel").pack(pady=40)
            return

        fig = plot_split_distribution(analytics) if self.chart_mode == "split" else plot_pace_trend(analytics)
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.figures.append(fig)
        self.canvas_widgets.append(canvas)
