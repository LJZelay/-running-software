import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import List, Optional
from datetime import datetime
import csv
import threading

from application.dto.runner_rest_view import RunnerRestView
from application.dto.runner_running_view import RunnerRunningView
from application.dto.runner_analytics_dto import RunnerAnalyticsDTO
from application.dto.workout_stats_dto import WorkoutStatsDTO
from domain.workout import Workout
from domain.runnerState import RunnerState
from domain.workoutState import WorkoutState
from externalInterface.csv_roster_parser import CSVRosterParser, CSVInputError
from externalInterface.csv_workout_config_parser import CSVWorkoutConfigParser
from externalInterface.reader_hardware_adapter import create_rfid_rest_adapter, create_nfc_adapter
from externalInterface.scanner_adapter import ScannerAdapter, ScannerPayload
from application.last_roster_service import LastRosterService
from externalInterface.runner_pdf_report_service import RunnerPdfReportService
from gui.analytics_widgets import (
    plot_pace_trend,
    plot_split_distribution,
    plot_run_vs_rest_time,
    plot_rest_efficiency,
    plot_average_pace_by_runner,
    plot_workout_progress
)
from gui.runner_view import RunnerView
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
        repo=None,
        workout_id: int = 1,
        start_workout_uc=None,
        end_workout_uc=None,
        add_runner_uc=None,
        nfc_uc=None,
        rfid_uc=None,
        refresh_interval_ms: int = 1000,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.get_rest_uc = get_rest_uc
        self.get_running_uc = get_running_uc
        self.get_runner_analytics_uc = get_runner_analytics_uc
        self.get_workout_stats_uc = get_workout_stats_uc
        self.repo = repo
        self.start_workout_uc = start_workout_uc
        self.end_workout_uc = end_workout_uc
        self.add_runner_uc = add_runner_uc
        self.nfc_uc = nfc_uc
        self.rfid_uc = rfid_uc
        self.workout_id = workout_id
        self.refresh_interval_ms = refresh_interval_ms
        self.chart_modes = ["pace", "split", "run_vs_rest", "rest_efficiency", "avg_pace", "progress"]
        self.chart_mode_index = 0
        self.workout_active = False
        self.runner_windows = []

        # Initialize hardware adapters and services
        self.rfid_adapter: Optional[ScannerAdapter] = None
        self.nfc_adapter: Optional[ScannerAdapter] = None
        self.scanning_active = False
        self.last_roster_service = LastRosterService()
        self.pdf_report_service = RunnerPdfReportService()
        self.scan_button = None  # Will be set when button is created

        ModernTheme.configure(parent)
        self._setup_ui()
        self._start_polling()
        
        # Bind cleanup on window destroy
        self.parent.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _setup_ui(self):
        """Create the UI widgets."""
        self.parent.title("Interval Training Management - Coach Dashboard")
        self.parent.geometry("1400x900")  # Increased size for better layout
        self.parent.minsize(1200, 700)   # Minimum size to prevent cramped layout

        toolbar = ttk.Frame(self, style="Toolbar.TFrame", padding=(16, 12))
        toolbar.pack(fill=tk.X, side=tk.TOP)

        # Title with proper hierarchy
        title_label = ttk.Label(toolbar, text="Interval Training", style="Title.TLabel")
        title_label.pack(side=tk.LEFT, padx=(0, 24))

        # Supplementary guidance text
        toolbar_tip = ttk.Label(toolbar,
                                text="Manage your workout roster, live status, and analytics from one polished dashboard.",
                                style="Tip.TLabel")
        toolbar_tip.pack(side=tk.LEFT, pady=(8, 0))

        # Status badge with subtle styling
        self.status_var = tk.StringVar(value="Standby")
        self.status_badge = tk.Canvas(toolbar, width=160, height=28, bg=ModernTheme.BG_DARK, highlightthickness=0)
        self.status_badge.pack(side=tk.RIGHT, padx=(0, 16))
        self._update_status_badge(self.status_var.get())

        self.workout_info_var = tk.StringVar(value="Workout: 400m x1 INDIVIDUAL")
        self.workout_info_label = ttk.Label(toolbar, textvariable=self.workout_info_var, style="Tip.TLabel")
        self.workout_info_label.pack(side=tk.RIGHT, padx=(0, 16))

        # Action buttons with proper spacing and hierarchy
        action_frame = ttk.Frame(self, style="GlassHighlight.TFrame")
        action_frame.pack(fill=tk.X, pady=(8, 16))

        # Primary actions (Start/End workout) - Top row
        primary_frame = ttk.Frame(action_frame, style="GlassHighlight.TFrame")
        primary_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.btn_start = ttk.Button(primary_frame, text="▶ Start Workout",
                                   command=self._on_start_workout, style="Success.TButton")
        self.btn_start.pack(side=tk.LEFT, padx=(0, 12), pady=4)

        self.btn_end = ttk.Button(primary_frame, text="⏹ End Workout",
                                 command=self._on_end_workout, style="Danger.TButton", state=tk.DISABLED)
        self.btn_end.pack(side=tk.LEFT, padx=(0, 24), pady=4)

        # Secondary actions - Second row with better organization
        secondary_frame = ttk.Frame(action_frame, style="GlassHighlight.TFrame")
        secondary_frame.pack(fill=tk.X, pady=(0, 8))

        # Roster management buttons
        ttk.Button(secondary_frame, text="📂 Load Roster",
                  command=self._on_load_roster, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(secondary_frame, text="💾 Save Roster",
                  command=self._on_save_last_roster, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(secondary_frame, text="📤 Load Last Roster",
                  command=self._on_load_last_roster, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
        
        # Separator
        ttk.Separator(secondary_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=4)
        
        # Workout and scanning buttons
        ttk.Button(secondary_frame, text="⚙ Load Workout",
                  command=self._on_load_workout, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
        self.scan_button = ttk.Button(secondary_frame, text="📡 Start Scanning",
                  command=self._on_toggle_scanning, style="Secondary.TButton")
        self.scan_button.pack(side=tk.LEFT, padx=(0, 8))
        
        # Separator
        ttk.Separator(secondary_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=4)
        
        # Utility buttons
        ttk.Button(secondary_frame, text="🔄 Refresh",
                  command=self._on_refresh, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(secondary_frame, text="👤 Runner Details",
                  command=self._on_open_selected_runner, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(secondary_frame, text="📊 Charts",
                  command=self._on_toggle_chart, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
        
        # Separator
        ttk.Separator(secondary_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=4)
        
        # Export buttons
        ttk.Button(secondary_frame, text="📄 PDF Reports",
                  command=self._on_generate_pdf_reports, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(secondary_frame, text="💾 Export CSV",
                  command=self._on_export, style="Secondary.TButton").pack(side=tk.LEFT)

        # Coaching tip for better workflow
        ttk.Label(action_frame,
                  text="Tip: Load your roster first, then start the workout; refresh keeps live status current.",
                  style="Tip.TLabel").pack(side=tk.LEFT, padx=(16, 0), pady=(10, 0))

        # Main content area with proper spacing
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # Live Status Tab with glass-style cards
        self.live_frame = ttk.Frame(self, style="Glass.TFrame")
        self.live_frame.configure(padding=(20, 16))
        self.notebook.add(self.live_frame, text="🏃 Live Status", padding=8)

        # Live Status Tab content with proper spacing
        # Running athletes section
        running_section = ttk.LabelFrame(self.live_frame, text="🏃 Running Athletes", style="Card.TLabelframe")
        running_section.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        
        running_container = ttk.Frame(running_section, style="Card.TFrame")
        running_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.running_tree = ttk.Treeview(running_container, columns=("name", "int", "laps", "prog", "pace"), height=10, show="headings", style="Treeview")
        self.running_tree.heading("name", text="Name")
        self.running_tree.heading("int", text="Interval")
        self.running_tree.heading("laps", text="Laps")
        self.running_tree.heading("prog", text="Progress")
        self.running_tree.heading("pace", text="Avg Pace")
        self.running_tree.column("name", width=200, minwidth=150)
        self.running_tree.column("int", width=80, minwidth=60)
        self.running_tree.column("laps", width=80, minwidth=60)
        self.running_tree.column("prog", width=120, minwidth=100)
        self.running_tree.column("pace", width=100, minwidth=80)
        
        # Add scrollbar for running tree
        running_scrollbar = ttk.Scrollbar(running_container, orient=tk.VERTICAL, command=self.running_tree.yview)
        self.running_tree.configure(yscrollcommand=running_scrollbar.set)
        
        self.running_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        running_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.running_tree.bind("<Double-1>", self._on_running_row_double_click)

        # Resting athletes section
        resting_section = ttk.LabelFrame(self.live_frame, text="😴 Resting Athletes", style="Card.TLabelframe")
        resting_section.pack(fill=tk.BOTH, expand=True)
        
        resting_container = ttk.Frame(resting_section, style="Card.TFrame")
        resting_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.resting_tree = ttk.Treeview(resting_container, columns=("name", "time", "rdy", "next"), height=8, show="headings", style="Treeview")
        self.resting_tree.heading("name", text="Name")
        self.resting_tree.heading("time", text="Time Left")
        self.resting_tree.heading("rdy", text="Status")
        self.resting_tree.heading("next", text="Next Action")
        self.resting_tree.column("name", width=200, minwidth=150)
        self.resting_tree.column("time", width=120, minwidth=100)
        self.resting_tree.column("rdy", width=100, minwidth=80)
        self.resting_tree.column("next", width=120, minwidth=100)
        
        # Add scrollbar for resting tree
        resting_scrollbar = ttk.Scrollbar(resting_container, orient=tk.VERTICAL, command=self.resting_tree.yview)
        self.resting_tree.configure(yscrollcommand=resting_scrollbar.set)
        
        self.resting_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        resting_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.resting_tree.bind("<Double-1>", self._on_resting_row_double_click)

        # Status tip
        ttk.Label(self.live_frame, text="💡 Tip: Double-click any runner to open their personal dashboard. Runner windows auto-open when athletes start running.", 
                 style="Tip.TLabel").pack(anchor=tk.W, pady=(12, 0))

        # Analytics Tab with card styling
        self.analytics_frame = ttk.Frame(self, style="Card.TFrame")
        self.analytics_frame.configure(padding=(20, 16))
        self.notebook.add(self.analytics_frame, text="📊 Analytics", padding=8)

        # Analytics header with controls
        analytics_header = ttk.Frame(self.analytics_frame, style="Card.TFrame")
        analytics_header.pack(fill=tk.X, pady=(0, 16))
        
        ttk.Label(analytics_header, text="Workout Statistics", style="Header.TLabel").pack(side=tk.LEFT)
        
        # Chart mode selector
        chart_controls = ttk.Frame(analytics_header, style="Card.TFrame")
        chart_controls.pack(side=tk.RIGHT)
        
        ttk.Label(chart_controls, text="Chart:", style="Body.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        self.chart_mode_var = tk.StringVar(value="pace")
        chart_combo = ttk.Combobox(chart_controls, textvariable=self.chart_mode_var, 
                                  values=["pace", "split", "run_vs_rest", "rest_efficiency", "avg_pace", "progress"],
                                  state="readonly", width=15)
        chart_combo.pack(side=tk.LEFT, padx=(0, 8))
        chart_combo.bind("<<ComboboxSelected>>", lambda e: self._on_chart_mode_changed())
        
        ttk.Button(chart_controls, text="🔄 Refresh", 
                  command=self._update_analytics, style="Secondary.TButton").pack(side=tk.LEFT)

        self.stats_label = ttk.Label(self.analytics_frame, text="Loading...", style="Body.TLabel")
        self.stats_label.pack(anchor=tk.W, pady=(0, 16))

        self.chart_frame = ttk.Frame(self.analytics_frame, style="Surface.TFrame")
        self.chart_frame.configure(padding=(16, 12))
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

        self.figures = []
        self.canvas_widgets = []

        if self.repo:
            initial_workout = self.repo.get_by_id(self.workout_id)
            self._update_workout_info_label(initial_workout)

    def _update_status_badge(self, status: str, color: str = ModernTheme.WARNING):
        """Update status badge with smooth visual feedback."""
        self.status_var.set(status)
        self.status_badge.delete("all")
        # Draw rounded rectangle background
        self.status_badge.create_rounded_rect(4, 4, 156, 24, radius=8, fill=color, outline=color)
        # Status indicator dot
        self.status_badge.create_oval(12, 8, 18, 14, fill="white", outline="white")
        # Status text
        self.status_badge.create_text(32, 12, text=status, fill="white", font=("Helvetica", 10, "bold"), anchor="w")

    def _flash_status(self, color: str, duration_ms: int = 800):
        """Briefly flash the status badge for feedback."""
        original_color = ModernTheme.SUCCESS if self.workout_active else ModernTheme.WARNING
        self._update_status_badge("✓", color)
        self.after(duration_ms, lambda: self._update_status_badge(
            "Active ●" if self.workout_active else "Standby", original_color))

    def _flash_status_message(self, message: str, color: str, duration_ms: int = 2000):
        """Flash a custom status message briefly."""
        original_text = self.status_var.get()
        original_color = ModernTheme.SUCCESS if self.workout_active else ModernTheme.WARNING
        self._update_status_badge(message, color)
        self.after(duration_ms, lambda: self._update_status_badge(original_text, original_color))

    def _start_polling(self):
        self._poll()
        self.after(self.refresh_interval_ms, self._start_polling)

    def _poll(self):
        try:
            running = self.get_running_uc.execute(self.workout_id)
            self._update_running_table(running)
            # If the workout is loaded but not started, show the roster in standby mode.
            if not running:
                self._populate_standby_runners()
        except Exception:
            pass

        try:
            resting = self.get_rest_uc.execute(self.workout_id)
            self._update_resting_table(resting)
        except Exception:
            pass

        self._update_analytics()

    def _update_running_table(self, views: List[RunnerRunningView]):
        # Track which runners were previously running
        previous_running_ids = set()
        for item in self.running_tree.get_children():
            previous_running_ids.add(int(item))
        
        self.running_tree.delete(*self.running_tree.get_children())
        current_running_ids = set()
        
        for v in views:
            # For now, show N/A for pace since it's not in the DTO
            pace_display = "N/A"
            self.running_tree.insert("", tk.END, iid=str(v.runner_id), values=(v.runner_name, v.interval_number, v.laps_completed, f"{v.laps_completed}/{v.laps_per_interval}", pace_display))
            current_running_ids.add(v.runner_id)
            
            # Auto-open runner window if this runner just started running
            if v.runner_id not in previous_running_ids and v.interval_number > 0:
                self._auto_open_runner_window(v.runner_id)

    def _populate_standby_runners(self):
        if not self.repo:
            return False

        workout = self.repo.get_by_id(self.workout_id)
        if not workout or workout.status != WorkoutState.NOT_STARTED:
            return False

        if not getattr(workout, "runnerSessions", None):
            return False

        self.running_tree.delete(*self.running_tree.get_children())
        for rs in sorted(workout.runnerSessions, key=lambda session: session.runner.name):
            status_text = "Ready" if rs.state == RunnerState.READY else "Standby"
            self.running_tree.insert(
                "",
                tk.END,
                iid=str(rs.runner.id),
                values=(rs.runner.name, 0, 0, status_text, "N/A")
            )
        return True

    def _update_workout_info_label(self, workout: Workout):
        if not workout:
            self.workout_info_var.set("Workout: not loaded")
            return

        self.workout_info_var.set(
            f"Workout: {workout.intervalDistance}m x{workout.lapsPerInterval} {workout.startMode.title()}"
        )

    def _on_load_workout(self):
        file_path = filedialog.askopenfilename(
            title="Load Workout Info",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            parser = CSVWorkoutConfigParser()
            config = parser.parse_csv_file(file_path)

            target_workout_id = config.workout_id or self.workout_id
            workout = self.repo.get_by_id(target_workout_id) if self.repo else None

            if workout and workout.status != WorkoutState.NOT_STARTED:
                messagebox.showerror(
                    "Cannot Load Workout",
                    "Workout settings can only be changed before the workout starts."
                )
                return

            if not workout:
                workout = Workout(
                    workout_id=target_workout_id,
                    intervalDistance=config.interval_distance,
                    lapsPerInterval=config.laps_per_interval,
                    startMode=config.start_mode
                )
            else:
                workout.intervalDistance = config.interval_distance
                workout.lapsPerInterval = config.laps_per_interval
                workout.startMode = config.start_mode

            workout.status = WorkoutState.NOT_STARTED
            self.repo.save(workout)
            self.workout_id = target_workout_id
            self.workout_active = False
            self.btn_start.config(state=tk.NORMAL, text="▶ Start Workout")
            self.btn_end.config(state=tk.DISABLED, text="⏹ End Workout")
            self._update_workout_info_label(workout)
            self._poll()

            messagebox.showinfo(
                "Workout Loaded",
                f"Loaded workout: {workout.intervalDistance}m intervals, {workout.lapsPerInterval} laps, {workout.startMode}."
            )
            self._update_status_badge(
                f"Loaded {workout.intervalDistance}m x{workout.lapsPerInterval}",
                ModernTheme.SUCCESS
            )
        except CSVInputError as e:
            messagebox.showerror("Workout Parse Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load workout: {str(e)}")

    def _on_open_selected_runner(self):
        runner_id = self._get_selected_runner_id()
        if runner_id is None:
            messagebox.showinfo("Open Runner", "Select a runner from either the running or resting list.")
        else:
            self._open_runner_detail(runner_id)

    def _on_running_row_double_click(self, event):
        item_id = self.running_tree.identify_row(event.y)
        if item_id:
            self._open_runner_detail(int(item_id))

    def _on_resting_row_double_click(self, event):
        item_id = self.resting_tree.identify_row(event.y)
        if item_id:
            self._open_runner_detail(int(item_id))

    def _get_selected_runner_id(self):
        selection = self.running_tree.selection()
        if selection:
            return int(selection[0])
        selection = self.resting_tree.selection()
        if selection:
            return int(selection[0])
        return None

    def _open_runner_detail(self, runner_id: int):
        runner_session = self._find_runner_session_in_workout(runner_id)
        if not runner_session:
            messagebox.showwarning("Runner not found", "Could not find runner details for the selected athlete.")
            return

        existing_window = next((w for w in self.runner_windows if getattr(w, "runner_id", None) == runner_id), None)
        if existing_window:
            existing_window.lift()
            return

        runner_window = RunnerView(
            self.parent,
            self.get_rest_uc,
            self.get_runner_analytics_uc,
            runner_session.runner,
            self.workout_id,
            scan_nfc_uc=self.nfc_uc,
            scan_rfid_uc=self.rfid_uc
        )
        runner_window.protocol("WM_DELETE_WINDOW", lambda w=runner_window: self._on_close_runner_window(w))
        self.runner_windows.append(runner_window)

    def _on_close_runner_window(self, window):
        if window in self.runner_windows:
            self.runner_windows.remove(window)
        window.destroy()

    def _auto_open_runner_window(self, runner_id: int):
        """Automatically open a runner window when they start running."""
        runner_session = self._find_runner_session_in_workout(runner_id)
        if not runner_session:
            return

        # Check if window already exists
        existing_window = next((w for w in self.runner_windows if getattr(w, "runner_id", None) == runner_id), None)
        if existing_window:
            existing_window.lift()
            return

        # Create new runner window
        runner_window = RunnerView(
            self.parent,
            self.get_rest_uc,
            self.get_runner_analytics_uc,
            runner_session.runner,
            self.workout_id,
            scan_nfc_uc=self.nfc_uc,
            scan_rfid_uc=self.rfid_uc
        )
        runner_window.protocol("WM_DELETE_WINDOW", lambda w=runner_window: self._on_close_runner_window(w))
        self.runner_windows.append(runner_window)

    def _find_runner_session_in_workout(self, runner_id: int):
        if not self.repo:
            return None
        workout = self.repo.get_by_id(self.workout_id)
        if not workout:
            return None

        for rs in workout.runnerSessions:
            if rs.runner.id == runner_id:
                return rs
        return None

    def _update_resting_table(self, views: List[RunnerRestView]):
        self.resting_tree.delete(*self.resting_tree.get_children())
        for v in views:
            # Format remaining time nicely
            if v.remaining_rest_seconds > 0:
                minutes = v.remaining_rest_seconds // 60
                seconds = v.remaining_rest_seconds % 60
                time_display = f"{minutes}:{seconds:02d}"
            else:
                time_display = "Ready"
            
            status_display = "Ready" if v.is_ready_to_run else "Resting"
            next_action = "Scan to Run" if v.is_ready_to_run else f"Rest {time_display}"
            
            self.resting_tree.insert("", tk.END, iid=str(v.runner_id), values=(v.runner_name, time_display, status_display, next_action))

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
        self._flash_status(ModernTheme.SUCCESS)

    def _on_load_roster(self):
        """Load athlete roster from CSV file."""
        file_path = filedialog.askopenfilename(
            title="Load Athlete Roster",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            parser = CSVRosterParser()
            roster_data = parser.parse_csv_file(file_path)
            
            # Validate unique tags
            is_valid, errors = parser.validate_unique_tags(roster_data)
            if not is_valid:
                messagebox.showerror("CSV Error", f"Duplicate tags found:\n" + "\n".join(errors[:5]))
                return
            
            # Get or create workout
            if not self.repo:
                messagebox.showerror("Error", "Repository not available")
                return
            
            workout = self.repo.get_by_id(self.workout_id)
            if not workout:
                from domain.workout import Workout
                workout = Workout(workout_id=self.workout_id, intervalDistance=400, lapsPerInterval=1, startMode="INDIVIDUAL")
                self.repo.save(workout)
            else:
                # Clear existing runners
                workout.runnerSessions.clear()
            
            # Add runners to workout
            from domain.runner import Runner
            from domain.runnerSession import RunnerSession
            
            runner_id = 1
            for athlete in roster_data:
                runner = Runner(
                    runner_id=runner_id,
                    name=athlete.name,
                    email=athlete.email,
                    nfc_tag=athlete.nfc_id,
                    rfid_tag=athlete.rfid_id
                )
                runner_session = RunnerSession(runner=runner, restDuration=60)
                workout.add_runner_session(runner_session)
                runner_id += 1
            
            self.repo.save(workout)
            self.workout_active = workout.status == WorkoutState.ACTIVE
            self.btn_start.config(state=tk.NORMAL, text="▶ Start Workout")
            self.btn_end.config(state=tk.DISABLED, text="⏹ End Workout")

            # Save as last known roster
            runners = [session.runner for session in workout.runnerSessions]
            self.last_roster_service.save_roster(runners)

            # Refresh UI and show success message
            self._poll()
            messagebox.showinfo("Success", f"Loaded {len(roster_data)} athletes")
            self._update_status_badge(f"✓ {len(roster_data)} runners", ModernTheme.SUCCESS)
            
        except CSVInputError as e:
            messagebox.showerror("CSV Parse Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load roster: {str(e)}")

    def _on_toggle_chart(self):
        # Legacy method - now handled by combobox
        self.chart_mode_index = (self.chart_mode_index + 1) % len(self.chart_modes)
        self.chart_mode_var.set(self.chart_modes[self.chart_mode_index])
        self._update_analytics()

    def _on_chart_mode_changed(self):
        """Handle chart mode selection from combobox."""
        selected_mode = self.chart_mode_var.get()
        if selected_mode in self.chart_modes:
            self.chart_mode_index = self.chart_modes.index(selected_mode)
            self._update_analytics()

    def _on_start_workout(self):
        try:
            if not self.start_workout_uc:
                raise RuntimeError("Start workout use case is not configured.")

            if not self.repo:
                raise RuntimeError("Workout repository is not available.")

            workout = self.repo.get_by_id(self.workout_id)
            if workout is None:
                raise RuntimeError(f"Workout #{self.workout_id} is not loaded.")

            if workout.status != WorkoutState.NOT_STARTED:
                raise RuntimeError(f"Workout cannot start because it is already {workout.status.value.replace('_', ' ').lower()}.")

            if not getattr(workout, 'runnerSessions', None):
                raise RuntimeError("No runners are loaded. Load a roster before starting the workout.")

            # Provide immediate feedback
            self._flash_status_message("Starting workout...", ModernTheme.INFO)
            self.btn_start.config(state=tk.DISABLED, text="⏳ Starting...")

            started = self.start_workout_uc.execute(self.workout_id)
            if not started:
                raise RuntimeError("Workout start was blocked by the current workout state.")

            self.workout_active = True

            # Update button states with clear visual hierarchy
            self.btn_start.config(state=tk.DISABLED, text="▶ Started")
            self.btn_end.config(state=tk.NORMAL)

            # Success feedback with clear status
            self._update_status_badge("▶ Active", ModernTheme.SUCCESS)
            self._flash_status_message("Workout started successfully!", ModernTheme.SUCCESS)

        except Exception as e:
            self.btn_start.config(state=tk.NORMAL, text="▶ Start Workout")
            self._update_status_badge("❌ Start Failed", ModernTheme.DANGER)
            self._show_start_workout_error(e)

    def _show_start_workout_error(self, error: Exception):
        message = str(error) or "An unknown error occurred while starting the workout."
        details = [
            "Please check the following:",
            "• A workout must exist and be loaded.",
            "• The workout must be in the Not Started state.",
            "• At least one runner must be loaded before starting.",
            "• The repository and start use case must be configured correctly.",
            "", 
            f"Details: {message}"
        ]
        messagebox.showerror("Failed to Start Workout", "\n".join(details))
        self._flash_status_message(message, ModernTheme.DANGER)

    def _on_end_workout(self):
        # Forgiveness principle: Confirm destructive action
        if not messagebox.askyesno("End Workout",
                                  "Are you sure you want to end the workout?\n\nThis will stop all runners and finalize the session.",
                                  icon='warning'):
            return

        try:
            if self.end_workout_uc:
                # Provide immediate feedback
                self._flash_status_message("Ending workout...", ModernTheme.WARNING)
                self.btn_end.config(state=tk.DISABLED, text="⏳ Ending...")

                self.end_workout_uc.execute(self.workout_id)
                self.workout_active = False

                # Update button states with clear visual hierarchy
                self.btn_start.config(state=tk.NORMAL, text="▶ Start Workout")
                self.btn_end.config(state=tk.DISABLED, text="⏹ End Workout")

                # Clear completion feedback
                self._update_status_badge("⏹ Completed", ModernTheme.INFO)
                self._flash_status_message("Workout ended successfully!", ModernTheme.SUCCESS)

        except Exception as e:
            # Error recovery with clear feedback
            self.btn_end.config(state=tk.NORMAL, text="⏹ End Workout")
            self._update_status_badge("❌ End Failed", ModernTheme.DANGER)
            self._flash_status_message(f"Failed to end workout: {str(e)}", ModernTheme.DANGER)

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

        current_mode = self.chart_modes[self.chart_mode_index]
        
        if current_mode == "pace":
            fig = plot_pace_trend(analytics)
        elif current_mode == "split":
            fig = plot_split_distribution(analytics)
        elif current_mode == "run_vs_rest":
            fig = plot_run_vs_rest_time(analytics)
        elif current_mode == "rest_efficiency":
            fig = plot_rest_efficiency(analytics)
        elif current_mode == "avg_pace":
            fig = plot_average_pace_by_runner(analytics)
        elif current_mode == "progress":
            fig = plot_workout_progress(analytics)
        else:
            fig = plot_pace_trend(analytics)
        
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.figures.append(fig)
        self.canvas_widgets.append(canvas)

    def _on_save_last_roster(self):
        """Save current roster as the last known roster."""
        try:
            if not self.repo:
                messagebox.showerror("Error", "Repository not available")
                return

            workout = self.repo.get_by_id(self.workout_id)
            if not workout or not hasattr(workout, 'runnerSessions') or not workout.runnerSessions:
                messagebox.showerror("Error", "No roster loaded to save")
                return

            runners = [session.runner for session in workout.runnerSessions]
            self.last_roster_service.save_roster(runners)
            self._update_status_badge("✓ Roster Saved", ModernTheme.SUCCESS)
            messagebox.showinfo("Success", "Roster saved as last known roster")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save roster: {str(e)}")
            self._update_status_badge("Save Failed", ModernTheme.DANGER)

    def _on_load_last_roster(self):
        """Load the last known roster."""
        try:
            if not self.last_roster_service.has_saved_roster():
                messagebox.showerror("Error", "No saved roster found")
                return

            runners = self.last_roster_service.load_roster()
            if not runners:
                messagebox.showerror("Error", "Saved roster is empty")
                return

            if not self.repo:
                messagebox.showerror("Error", "Repository not available")
                return

            workout = self.repo.get_by_id(self.workout_id)
            if not workout:
                from domain.workout import Workout
                workout = Workout(workout_id=self.workout_id, intervalDistance=400, lapsPerInterval=1, startMode="INDIVIDUAL")
                self.repo.save(workout)
            else:
                # Clear existing runners
                workout.runnerSessions.clear()

            # Add runners to workout
            from domain.runnerSession import RunnerSession
            for runner in runners:
                runner_session = RunnerSession(runner=runner, restDuration=60)
                workout.add_runner_session(runner_session)

            self.repo.save(workout)
            self.workout_active = workout.status == WorkoutState.ACTIVE
            self.btn_start.config(state=tk.NORMAL, text="▶ Start Workout")
            self.btn_end.config(state=tk.DISABLED, text="⏹ End Workout")

            # Refresh UI and show success message
            self._poll()
            messagebox.showinfo("Success", f"Loaded {len(runners)} runners from saved roster")
            self._update_status_badge(f"✓ {len(runners)} runners", ModernTheme.SUCCESS)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load roster: {str(e)}")
            self._update_status_badge("Load Failed", ModernTheme.DANGER)

    def _on_generate_pdf_reports(self):
        """Generate PDF reports for all runners in the workout."""
        try:
            if not self.repo:
                messagebox.showerror("Error", "Repository not available")
                return

            workout = self.repo.get_by_id(self.workout_id)
            if not workout:
                messagebox.showerror("Error", "No workout loaded")
                return

            if workout.status != WorkoutState.COMPLETED:
                result = messagebox.askyesno("Warning", 
                    "Workout is not completed. Generate reports anyway?", 
                    icon='warning')
                if not result:
                    return

            generated_files = self.pdf_report_service.generate_reports_for_workout(workout)
            
            if generated_files:
                messagebox.showinfo("Success", 
                    f"Generated {len(generated_files)} PDF reports in 'reports' folder")
                self._update_status_badge(f"✓ {len(generated_files)} PDFs", ModernTheme.SUCCESS)
            else:
                messagebox.showinfo("Info", "No reports generated (no completed intervals)")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF reports: {str(e)}")
            self._update_status_badge("PDF Failed", ModernTheme.DANGER)

    def _on_toggle_scanning(self):
        """Start or stop hardware scanning for RFID/NFC."""
        try:
            if self.scanning_active:
                self._stop_scanning()
            else:
                self._start_scanning()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle scanning: {str(e)}")
            self._update_status_badge("Scan Error", ModernTheme.DANGER)

    def _start_scanning(self):
        """Initialize and start hardware scanning."""
        try:
            # Initialize RFID adapter (you may need to configure the scanner address)
            rfid_scanner_address = "localhost:5084"  # Default Impinj REST endpoint
            self.rfid_adapter = create_rfid_rest_adapter(rfid_scanner_address)
            
            # Initialize NFC adapter
            self.nfc_adapter = create_nfc_adapter()
            
            # Set up event callbacks
            self.rfid_adapter.set_event_callback(self._on_scanner_event)
            self.nfc_adapter.set_event_callback(self._on_scanner_event)
            
            # Start adapters
            self.rfid_adapter.start()
            self.nfc_adapter.start()
            
            self.scanning_active = True
            self._update_status_badge("🔍 Scanning", ModernTheme.INFO)
            
            # Update button text
            if self.scan_button:
                self.scan_button.config(text="⏹ Stop Scanning")
                    
        except ConnectionError as e:
            self._cleanup_adapters()
            messagebox.showerror("Connection Error", f"Failed to connect to hardware scanner: {str(e)}")
            raise
        except Exception as e:
            self._cleanup_adapters()
            messagebox.showerror("Scanner Error", f"Failed to initialize scanners: {str(e)}")
            raise
            self.nfc_adapter = None

    def _on_scanner_event(self, payload: ScannerPayload):
        """Handle scanner events from hardware."""
        try:
            timestamp_str = datetime.fromtimestamp(payload.timestamp_ms / 1000).isoformat()
            
            if payload.event_type == "RFID":
                if self.rfid_uc:
                    result = self.rfid_uc.execute(self.workout_id, payload.tag_id, timestamp_str, use_event_time=True)
                    if result.decision.value == "ACCEPTED":
                        self._flash_status_message(f"RFID: {payload.tag_id[:8]}...", ModernTheme.SUCCESS, 1000)
                    else:
                        self._flash_status_message(f"RFID rejected: {result.reason.value}", ModernTheme.WARNING, 1500)
                        
            elif payload.event_type == "NFC":
                if self.nfc_uc:
                    result = self.nfc_uc.execute(self.workout_id, payload.tag_id, timestamp_str, use_event_time=True)
                    self._flash_status_message(f"NFC: {payload.tag_id[:8]}...", ModernTheme.SUCCESS, 1000)
                    
            # Refresh the UI to show updated status
            self.after(500, self._poll)
            
        except Exception as e:
            print(f"Error processing scanner event: {e}")
            self._flash_status_message("Scan Error", ModernTheme.DANGER, 2000)

    def _on_window_close(self):
        """Handle window close event with proper cleanup."""
        self._stop_scanning()
        self.parent.destroy()


# Canvas utility methods for Apple-style rounded rectangles
def _add_canvas_methods():
    """Add rounded rectangle method to Canvas."""
    def create_rounded_rect(self, x1, y1, x2, y2, radius=8, **kwargs):
        """Create a rounded rectangle on the canvas."""
        # Create the rounded rectangle using arcs and lines
        self.create_arc(x1, y1, x1 + 2*radius, y1 + 2*radius, start=90, extent=90, **kwargs)
        self.create_arc(x2 - 2*radius, y1, x2, y1 + 2*radius, start=0, extent=90, **kwargs)
        self.create_arc(x1, y2 - 2*radius, x1 + 2*radius, y2, start=180, extent=90, **kwargs)
        self.create_arc(x2 - 2*radius, y2 - 2*radius, x2, y2, start=270, extent=90, **kwargs)
        # Fill the sides
        self.create_rectangle(x1 + radius, y1, x2 - radius, y2, **kwargs)
        self.create_rectangle(x1, y1 + radius, x2, y2 - radius, **kwargs)

    tk.Canvas.create_rounded_rect = create_rounded_rect

_add_canvas_methods()
