import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import List, Optional
from datetime import datetime
import csv
import threading
import time

from application.dto.runner_rest_view import RunnerRestView
from application.dto.runner_running_view import RunnerRunningView
from application.dto.runner_analytics_dto import RunnerAnalyticsDTO
from application.dto.workout_stats_dto import WorkoutStatsDTO
from domain.workout import Workout
from domain.runnerState import RunnerState
from domain.workoutState import WorkoutState
from externalInterface.reader_hardware_adapter import create_rfid_rest_adapter, create_nfc_adapter
from externalInterface.scanner_event_utils import normalize_nfc_tag_id, normalize_rfid_tag_id
from externalInterface.scanner_adapter import ScannerAdapter, ScannerPayload
from application.last_roster_service import LastRosterService
from gui.analytics_widgets import (
    plot_pace_trend,
    plot_pace_trend_for_single,
)
from gui.runner_view import RunnerView
from gui.theme import ModernTheme
from gui.timestamp_editor_view import TimestampEditorView

from application.workout_repo import save_workout_summary, StorageThresholdWarning
from gui.workout_repo_page import WorkoutRepoPage
from externalInterface.workout_summary_pdf import WorkoutSummaryPdfGenerator
from tkinter import filedialog
from pathlib import Path
import json


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
        generate_report_uc=None,
        load_workout_config_uc=None,
        load_roster_uc=None,
        edit_timestamp_uc=None,
        undo_last_edit_uc=None,
        group_start_uc=None,
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
        self.generate_report_uc = generate_report_uc
        self.load_workout_config_uc = load_workout_config_uc
        self.load_roster_uc = load_roster_uc
        self.current_workout_id = workout_id
        self.workout_id = workout_id  # Deprecated, kept for backward compatibility
        self.edit_timestamp_uc = edit_timestamp_uc
        self.undo_last_edit_uc = undo_last_edit_uc
        self.refresh_interval_ms = refresh_interval_ms
        self.workout_active = False
        self.runner_windows = []
        self.auto_open_runner_windows = False
        self._auto_opened_runner_ids = set()
        self.default_rest_duration = 60
        self.workout_target_intervals = 4
        self.analytics_min_refresh_seconds = 4.0
        self.last_analytics_update_at = 0.0
        self.last_analytics_signature = None
        self._cached_analytics_workout_id = None
        self.group_start_uc = group_start_uc
        self._cached_runner_analytics = None
        self._cached_workout_stats = None

        # For matplotlib figures and canvas widgets
        self.figures = []
        self.canvas_widgets = []

        # Initialize hardware adapters and services
        self.rfid_adapter: Optional[ScannerAdapter] = None
        self.nfc_adapter: Optional[ScannerAdapter] = None
        self.scanning_active = False
        self.last_roster_service = LastRosterService()
        self.scan_button = None  # Will be set when button is created

        ModernTheme.configure(parent)
        self._setup_ui()
        self._start_polling()

        # Bind cleanup on window destroy
        self.parent.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _generate_new_workout_id(self) -> int:
        """Generate a unique workout ID based on current timestamp."""
        return int(datetime.now().timestamp() * 1000)

    def _new_workout_session(self):
        """Start a new workout session: generate new workout ID and reset state."""
        if self.workout_active:
            if not messagebox.askyesno(
                "Active Workout",
                "A workout is in progress. End it before starting a new session?",
                icon='warning'
            ):
                return
            self._on_end_workout()

        self.current_workout_id = self._generate_new_workout_id()
        self.workout_active = False
        self._clear_analytics_cache()
        self._auto_opened_runner_ids.clear()

        # Close all open runner windows
        for window in self.runner_windows:
            try:
                window.destroy()
            except:
                pass
        self.runner_windows.clear()

        if self.repo:
            from domain.workout import Workout
            workout = Workout(
                workout_id=self.current_workout_id,
                intervalDistance=400,
                lapsPerInterval=1,
                startMode="INDIVIDUAL"
            )
            self.repo.save(workout)

        self.btn_start.config(state=tk.NORMAL, text="▶ Start Workout")
        self.btn_end.config(state=tk.DISABLED, text="⏹ End Workout")
        self._update_workout_info_label(None)
        self._poll()

        messagebox.showinfo(
            "New Workout",
            f"Created new workout session with ID {self.current_workout_id}.\nLoad a roster and configure as needed."
        )

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
        ttk.Button(secondary_frame, text="🛠 Pre-Config",
                  command=self._on_preconfigure_workout, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(secondary_frame, text="⚙ Load Workout",
                  command=self._on_load_workout_repo_page, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
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
        self.btn_review = ttk.Button(secondary_frame, text="🔍 Review Workout",
                  command=self._on_edit_timestamps, style="Secondary.TButton", state=tk.DISABLED)
        self.btn_review.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(secondary_frame, text="📊 Charts",
                  command=self._on_toggle_chart, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
        
        # Separator
        ttk.Separator(secondary_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=4)
        
        # Export buttons
        ttk.Button(secondary_frame, text="📄 PDF Reports",
                  command=self._on_generate_pdf_reports, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(secondary_frame, text="💾 Export CSV",
                  command=self._on_export, style="Secondary.TButton").pack(side=tk.LEFT)

        # New Workout button
        ttk.Button(secondary_frame, text="🆕 New Workout",
                  command=self._new_workout_session, style="Primary.TButton").pack(side=tk.LEFT, padx=(16, 0))

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

        self.live_canvas = tk.Canvas(self.live_frame, highlightthickness=0, bg=ModernTheme.BG_DARK)
        live_scrollbar = ttk.Scrollbar(self.live_frame, orient=tk.VERTICAL, command=self.live_canvas.yview)
        self.live_canvas.configure(yscrollcommand=live_scrollbar.set)
        self.live_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        live_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.live_content = ttk.Frame(self.live_canvas, style="Glass.TFrame")
        self.live_content_id = self.live_canvas.create_window((0, 0), window=self.live_content, anchor="nw")

        def _sync_live_scrollregion(event):
            self.live_canvas.configure(scrollregion=self.live_canvas.bbox("all"))
            self.live_canvas.itemconfigure(self.live_content_id, width=event.width)

        self.live_content.bind("<Configure>", lambda e: self.live_canvas.configure(scrollregion=self.live_canvas.bbox("all")))
        self.live_canvas.bind("<Configure>", _sync_live_scrollregion)

        def _on_live_tab_mousewheel(event):
            # Only scroll if the Live Status tab is selected (index 0)
            if self.notebook.index(self.notebook.select()) == 0:
                # event.delta is positive for scroll up, negative for down (Windows/Mac)
                # For Linux, event.num == 4/5; we handle both via unified delta logic
                return "break"
            if hasattr(event, 'delta'):
                scroll_units = int(-1 * (event.delta / 120))
            else:
                # Linux Button-4 (up) -> -1, Button-5 (down) -> +1
                scroll_units = -1 if event.num == 4 else 1
                self.live_canvas.yview_scroll(scroll_units, "units")
            return "break"   # Prevent other widgets from also scrolling

        # Bind to the entire application window (makes it work even if mouse is over a treeview)
        self.parent.bind_all("<MouseWheel>", _on_live_tab_mousewheel)
        self.parent.bind_all("<Button-4>", _on_live_tab_mousewheel)   # Linux scroll up
        self.parent.bind_all("<Button-5>", _on_live_tab_mousewheel)   # Linux scroll down

        # Live Status Tab content with proper spacing
        # Running athletes section
        running_section = ttk.LabelFrame(self.live_content, text="🏃 Running Athletes", style="Card.TLabelframe")
        running_section.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        
        running_container = ttk.Frame(running_section, style="Card.TFrame")
        running_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.running_tree = ttk.Treeview(running_container, columns=("first_name", "last_name", "int", "laps", "prog", "pace"), height=10, show="headings", style="Treeview")
        self.running_tree.heading("first_name", text="First Name")
        self.running_tree.heading("last_name", text="Last Name")
        self.running_tree.heading("int", text="Interval")
        self.running_tree.heading("laps", text="Laps")
        self.running_tree.heading("prog", text="Progress")
        self.running_tree.heading("pace", text="Avg Pace")
        self.running_tree.column("first_name", width=100, minwidth=80)
        self.running_tree.column("last_name", width=100, minwidth=80)
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
        # Mouse wheel scroll for running_tree
        #self._bind_mousewheel(self.running_tree, running_scrollbar)

        # Resting athletes section
        resting_section = ttk.LabelFrame(self.live_content, text="😴 Resting Athletes", style="Card.TLabelframe")
        resting_section.pack(fill=tk.BOTH, expand=True)
        
        resting_container = ttk.Frame(resting_section, style="Card.TFrame")
        resting_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.resting_tree = ttk.Treeview(resting_container, columns=("first_name", "last_name", "time", "rdy", "next"), height=8, show="headings", style="Treeview")
        self.resting_tree.heading("first_name", text="First Name")
        self.resting_tree.heading("last_name", text="Last Name")
        self.resting_tree.heading("time", text="Time Left")
        self.resting_tree.heading("rdy", text="Status")
        self.resting_tree.heading("next", text="Next Action")
        self.resting_tree.column("first_name", width=100, minwidth=80)
        self.resting_tree.column("last_name", width=100, minwidth=80)
        self.resting_tree.column("time", width=120, minwidth=100)
        self.resting_tree.column("rdy", width=100, minwidth=80)
        self.resting_tree.column("next", width=120, minwidth=100)
        # Add scrollbar for resting tree
        resting_scrollbar = ttk.Scrollbar(resting_container, orient=tk.VERTICAL, command=self.resting_tree.yview)
        self.resting_tree.configure(yscrollcommand=resting_scrollbar.set)
        self.resting_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        resting_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.resting_tree.bind("<Double-1>", self._on_resting_row_double_click)
        # Mouse wheel scroll for resting_tree
        #self._bind_mousewheel(self.resting_tree, resting_scrollbar)

        # Finished athletes section
        finished_section = ttk.LabelFrame(self.live_content, text="✅ Finished Athletes", style="Card.TLabelframe")
        finished_section.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        finished_container = ttk.Frame(finished_section, style="Card.TFrame")
        finished_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.finished_tree = ttk.Treeview(
            finished_container,
            columns=("first_name", "last_name", "progress", "laps", "pace", "status"),
            height=6,
            show="headings",
            style="Treeview",
        )
        self.finished_tree.heading("first_name", text="First Name")
        self.finished_tree.heading("last_name", text="Last Name")
        self.finished_tree.heading("progress", text="Intervals")
        self.finished_tree.heading("laps", text="Total Laps")
        self.finished_tree.heading("pace", text="Avg Pace")
        self.finished_tree.heading("status", text="Status")
        self.finished_tree.column("first_name", width=100, minwidth=80)
        self.finished_tree.column("last_name", width=100, minwidth=80)
        self.finished_tree.column("progress", width=120, minwidth=100)
        self.finished_tree.column("laps", width=100, minwidth=80)
        self.finished_tree.column("pace", width=120, minwidth=100)
        self.finished_tree.column("status", width=120, minwidth=100)
        finished_scrollbar = ttk.Scrollbar(finished_container, orient=tk.VERTICAL, command=self.finished_tree.yview)
        self.finished_tree.configure(yscrollcommand=finished_scrollbar.set)
        self.finished_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.finished_tree.bind("<Double-1>", self._on_finished_row_double_click)
        finished_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        # Mouse wheel scroll for finished_tree
        #self._bind_mousewheel(self.finished_tree, finished_scrollbar)

        # Status tip
        ttk.Label(self.live_content, text="💡 Tip: Double-click any runner to open their personal dashboard. Runner windows auto-open when athletes start running.", 
                 style="Tip.TLabel").pack(anchor=tk.W, pady=(12, 0))

        # Analytics Tab with card styling
        self.analytics_frame = ttk.Frame(self, style="Card.TFrame")
        self.analytics_frame.configure(padding=(20, 16))
        self.notebook.add(self.analytics_frame, text="📊 Analytics", padding=8)

        # Analytics header with controls
        analytics_header = ttk.Frame(self.analytics_frame, style="Card.TFrame")
        analytics_header.pack(fill=tk.X, pady=(0, 16))
        
        ttk.Label(analytics_header, text="Workout Statistics", style="Header.TLabel").pack(side=tk.LEFT)
        
        chart_controls = ttk.Frame(analytics_header, style="Card.TFrame")
        chart_controls.pack(side=tk.RIGHT)
        
        ttk.Button(chart_controls, text="🔄 Refresh", 
                  command=lambda: self._update_analytics(force=True), style="Secondary.TButton").pack(side=tk.LEFT)

        self.stats_label = ttk.Label(self.analytics_frame, text="Loading...", style="Body.TLabel")
        self.stats_label.pack(anchor=tk.W, pady=(0, 16))

        self.analytics_tabs = ttk.Notebook(self.analytics_frame)
        self.analytics_tabs.pack(fill=tk.BOTH, expand=True)

        self.analytics_summary_tab = ttk.Frame(self.analytics_tabs, style="Surface.TFrame")
        self.analytics_summary_tab.configure(padding=(8, 8))
        self.analytics_tabs.add(self.analytics_summary_tab, text="Summary")

        self.analytics_runners_tab = ttk.Frame(self.analytics_tabs, style="Surface.TFrame")
        self.analytics_runners_tab.configure(padding=(8, 8))
        self.analytics_tabs.add(self.analytics_runners_tab, text="By Runner")

        self.chart_frame = ttk.Frame(self.analytics_summary_tab, style="Surface.TFrame")
        self.chart_frame.configure(padding=(16, 12))
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

        # --- Refactored: Runner List and Detail Pane ---
        self.runner_list_frame = ttk.Frame(self.analytics_runners_tab)
        self.runner_list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8), pady=4)
        # Title for the runner list
        ttk.Label(self.runner_list_frame, text="Runners", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4), padx=2)

        # Add a vertical scrollbar to the runner list
        self.runner_list_scrollbar = ttk.Scrollbar(self.runner_list_frame, orient=tk.VERTICAL)
        self.runner_tree = ttk.Treeview(
            self.runner_list_frame,
            columns=("first_name",),
            show="headings",
            selectmode="browse",
            height=20,
            yscrollcommand=self.runner_list_scrollbar.set
        )
        self.runner_list_scrollbar.config(command=self.runner_tree.yview)
        self.runner_tree.heading("first_name", text="First Name")
        self.runner_tree.column("first_name", width=100)
        self.runner_tree.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        self.runner_list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.runner_tree.bind("<<TreeviewSelect>>", self._on_runner_selected)
        # Mouse wheel scroll for runner_tree
        self._bind_mousewheel(self.runner_tree, self.runner_list_scrollbar)

        # Runner detail area with scrollable canvas (moved from _bind_mousewheel)
        self.runner_detail_outer = ttk.Frame(self.analytics_runners_tab)
        self.runner_detail_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
        self.runner_detail_canvas = tk.Canvas(self.runner_detail_outer, highlightthickness=0, bg=ModernTheme.BG_DARK)
        self.runner_detail_scrollbar = ttk.Scrollbar(self.runner_detail_outer, orient=tk.VERTICAL, command=self.runner_detail_canvas.yview)
        self.runner_detail_canvas.configure(yscrollcommand=self.runner_detail_scrollbar.set)
        self.runner_detail_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.runner_detail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.runner_detail_frame = ttk.Frame(self.runner_detail_canvas, style="Surface.TFrame")
        self.runner_detail_id = self.runner_detail_canvas.create_window((0, 0), window=self.runner_detail_frame, anchor="nw")

        def _sync_runner_detail_scrollregion(event):
            self.runner_detail_canvas.configure(scrollregion=self.runner_detail_canvas.bbox("all"))
            self.runner_detail_canvas.itemconfigure(self.runner_detail_id, width=event.width)

        self.runner_detail_frame.bind("<Configure>", lambda e: self.runner_detail_canvas.configure(scrollregion=self.runner_detail_canvas.bbox("all")))
        self.runner_detail_canvas.bind("<Configure>", _sync_runner_detail_scrollregion)

        # Mousewheel handler for runner_detail_canvas (bind only after attribute exists)
        def _scroll_runner_detail(event):
            if hasattr(event, 'delta'):
                scroll_units = int(-1 * (event.delta / 120))
            else:
                scroll_units = -1 if event.num == 4 else 1
            self.runner_detail_canvas.yview_scroll(scroll_units, "units")
            return "break"

        self.runner_detail_canvas.bind("<MouseWheel>", _scroll_runner_detail)
        self.runner_detail_canvas.bind("<Button-4>", _scroll_runner_detail)
        self.runner_detail_canvas.bind("<Button-5>", _scroll_runner_detail)

    def _on_finished_row_double_click(self, event):
        item_id = self.finished_tree.identify_row(event.y)
        if item_id and item_id.startswith("finished-"):
            runner_id = int(item_id.split("-", 1)[1])
            self._open_runner_detail(runner_id)

    def _bind_mousewheel(self, widget, scrollbar):
        # Cross-platform mousewheel binding for Treeview widgets
        def _on_mousewheel(event):
            if event.num == 4 or event.delta > 0:
                widget.yview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0:
                widget.yview_scroll(1, "units")
            return "break"

        # Windows and MacOS
        widget.bind("<MouseWheel>", _on_mousewheel)
        # Linux (event.num 4/5)
        widget.bind("<Button-4>", _on_mousewheel)
        widget.bind("<Button-5>", _on_mousewheel)

    def _on_load_workout_repo_page(self):
        print("OPENING REPO PAGE")
        WorkoutRepoPage(self.parent)

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
            running = self.get_running_uc.execute(self.current_workout_id)
            self._update_running_table(running)
            # If the workout is loaded but not started, show the roster in standby mode.
            if not running:
                self._populate_standby_runners()
        except Exception:
            pass

        try:
            resting = self.get_rest_uc.execute(self.current_workout_id)
            self._update_resting_table(resting)
        except Exception:
            pass

        self._update_finished_table()
        self._update_analytics()

        # Review Workout is a post-workout action: enable only when completed.
        try:
            btn = getattr(self, "btn_review", None)
            if btn is not None:
                workout = self.repo.get_by_id(self.workout_id) if self.repo else None
                if workout and workout.status == WorkoutState.COMPLETED:
                    btn.config(state=tk.NORMAL)
                else:
                    btn.config(state=tk.DISABLED)
        except Exception:
            pass

    def _update_running_table(self, views: List[RunnerRunningView]):
        # Track which runners were previously running
        previous_running_ids = set()
        for item in self.running_tree.get_children():
            previous_running_ids.add(int(item))
        
        # Preserve user selection across the rebuild so 1s poll doesn't steal it.
        preserved_selection = self.running_tree.selection()
        self.running_tree.delete(*self.running_tree.get_children())
        current_running_ids = set()
        
        for v in views:
            runner_session = self._find_runner_session_in_workout(v.runner_id)
            if runner_session and self._is_runner_finished(runner_session):
                continue

            # For now, show N/A for pace since it's not in the DTO
            pace_display = "N/A"
            laps_counter = f"{v.laps_completed}/{v.laps_per_interval}"
            laps_remaining = max(0, v.laps_per_interval - v.laps_completed)
            progress_label = f"{laps_counter} laps ({laps_remaining} to go)"
            # Split name into first and last
            name_parts = v.runner_name.split()
            first_name = name_parts[0] if len(name_parts) > 0 else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            self.running_tree.insert("", tk.END, iid=str(v.runner_id), values=(first_name, last_name, v.interval_number, laps_counter, progress_label, pace_display))
            current_running_ids.add(v.runner_id)
            # Auto-open runner window if this runner just started running
            if self.auto_open_runner_windows and v.runner_id not in previous_running_ids and v.interval_number > 0:
                self._auto_open_runner_window(v.runner_id)

        # Re-apply user selection for iids that still exist post-rebuild.
        still_present = [iid for iid in preserved_selection if self.running_tree.exists(iid)]
        if still_present:
            try:
                self.running_tree.selection_set(still_present)
            except Exception:
                pass

    def _populate_standby_runners(self):
        if not self.repo:
            return False

        workout = self.repo.get_by_id(self.current_workout_id)
        if not workout or workout.status != WorkoutState.NOT_STARTED:
            return False

        if not getattr(workout, "runnerSessions", None):
            return False

        preserved_selection = self.running_tree.selection()
        self.running_tree.delete(*self.running_tree.get_children())
        for rs in sorted(workout.runnerSessions, key=lambda session: session.runner.name):
            status_text = "Ready" if rs.state == RunnerState.READY else "Standby"
            name_parts = rs.runner.name.split()
            first_name = name_parts[0] if len(name_parts) > 0 else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            self.running_tree.insert(
                "",
                tk.END,
                iid=str(rs.runner.id),
                values=(first_name, last_name, 0, 0, status_text, "N/A")
            )
        still_present = [iid for iid in preserved_selection if self.running_tree.exists(iid)]
        if still_present:
            try:
                self.running_tree.selection_set(still_present)
            except Exception:
                pass
        return True

    def _update_workout_info_label(self, workout: Workout):
        if not workout:
            self.workout_info_var.set("Workout: not loaded")
            return

        self.workout_info_var.set(
            f"Workout: {workout.intervalDistance}m x{workout.lapsPerInterval} {workout.startMode.title()} | Target: {self.workout_target_intervals} intervals"
        )

    def _on_load_workout(self):
        try:
            from application.workout_repo import list_workouts, load_workout_summary
        except ImportError:
            messagebox.showerror("Error", "Persistent storage module not found.")
            return

        workouts = list_workouts()
        if not workouts:
            messagebox.showinfo("No Workouts", "No workouts found")
            return

        items = [f"{w.get('name', '')} ({w.get('date', '')})" for w in workouts]
        selected = simpledialog.askstring("Select Workout", "Choose workout by number:\n" + "\n".join(f"{i+1}. {item}" for i, item in enumerate(items)), parent=self.parent)
        if not selected:
            return
        try:
            idx = int(selected) - 1
            if idx < 0 or idx >= len(workouts):
                raise ValueError
        except Exception:
            messagebox.showerror("Invalid Selection", "Please enter a valid number.")
            return
        workout_id = workouts[idx]["workout_id"]
        data = load_workout_summary(workout_id)
        if not data:
            messagebox.showerror("Error", "Workout data not found.")
            return
        config = data.get("config", {})
        roster = data.get("roster", {})
        results = data.get("results", {})
        # Display config, roster, results in existing UI components if available
        if hasattr(self, "config_text"):
            self.config_text.delete("1.0", tk.END)
            self.config_text.insert(tk.END, str(config))
        if hasattr(self, "roster_text"):
            self.roster_text.delete("1.0", tk.END)
            self.roster_text.insert(tk.END, str(roster))
        if hasattr(self, "results_text"):
            self.results_text.delete("1.0", tk.END)
            self.results_text.insert(tk.END, str(results))
        messagebox.showinfo("Workout Loaded", f"Loaded workout: {workouts[idx].get('name','')} ({workouts[idx].get('date','')})")

    def _on_preconfigure_workout(self):
        """Prompt for workout settings without requiring CSV/hardcoded values."""
        if not self.repo:
            messagebox.showerror("Error", "Repository not available")
            return

        workout = self.repo.get_by_id(self.current_workout_id)
        if workout and workout.status == WorkoutState.ACTIVE:
            messagebox.showerror("Cannot Configure", "End workout before changing configuration.")
            return

        current_distance = workout.intervalDistance if workout else 400
        current_laps = workout.lapsPerInterval if workout else 1
        current_mode = workout.startMode if workout else "INDIVIDUAL"

        interval_distance = simpledialog.askinteger(
            "Pre-Config: Track Distance",
            "Distance around the track (meters):",
            parent=self.parent,
            initialvalue=current_distance,
            minvalue=1,
        )
        if interval_distance is None:
            return

        laps_per_interval = simpledialog.askinteger(
            "Pre-Config: Finish Threshold",
            "Laps required to finish an interval:",
            parent=self.parent,
            initialvalue=current_laps,
            minvalue=1,
        )
        if laps_per_interval is None:
            return

        rest_duration = simpledialog.askinteger(
            "Pre-Config: Rest Time",
            "Rest duration between intervals (seconds):",
            parent=self.parent,
            initialvalue=self.default_rest_duration,
            minvalue=0,
        )
        if rest_duration is None:
            return

        target_intervals = simpledialog.askinteger(
            "Pre-Config: Workout Target",
            "How many intervals to finish a runner?",
            parent=self.parent,
            initialvalue=self.workout_target_intervals,
            minvalue=1,
        )
        if target_intervals is None:
            return

        start_mode_input = simpledialog.askstring(
            "Pre-Config: Start Mode",
            "Start mode (INDIVIDUAL or GROUP):",
            parent=self.parent,
            initialvalue=current_mode,
        )
        if start_mode_input is None:
            return

        start_mode = start_mode_input.strip().upper() or "INDIVIDUAL"
        if start_mode not in {"INDIVIDUAL", "GROUP"}:
            messagebox.showerror("Invalid Start Mode", "Use INDIVIDUAL or GROUP")
            return

        if not workout or workout.status == WorkoutState.COMPLETED:
            from domain.runnerSession import RunnerSession
            preserved_runners = []
            if workout:
                preserved_runners = [rs.runner for rs in workout.runnerSessions]

            workout = Workout(
                workout_id=self.current_workout_id,
                intervalDistance=interval_distance,
                lapsPerInterval=laps_per_interval,
                startMode=start_mode,
            )
            for runner in preserved_runners:
                workout.add_runner_session(RunnerSession(runner=runner, restDuration=rest_duration))
        else:
            workout.intervalDistance = interval_distance
            workout.lapsPerInterval = laps_per_interval
            workout.startMode = start_mode
            for session in workout.runnerSessions:
                session.restDuration = rest_duration

        self.default_rest_duration = rest_duration
        self.workout_target_intervals = target_intervals
        workout.status = WorkoutState.NOT_STARTED
        self.repo.save(workout)
        self.workout_active = False
        self.btn_start.config(state=tk.NORMAL, text="▶ Start Workout")
        self.btn_end.config(state=tk.DISABLED, text="⏹ End Workout")
        self._clear_analytics_cache()
        self._update_workout_info_label(workout)
        self._poll()
        messagebox.showinfo(
            "Workout Configured",
            f"Distance: {interval_distance}m\n"
            f"Finish threshold: {laps_per_interval} laps/interval\n"
            f"Rest: {rest_duration}s\n"
            f"Workout target: {target_intervals} intervals\n"
            f"Start mode: {start_mode}"
        )
        self._update_status_badge("✓ Config Saved", ModernTheme.SUCCESS)

    def _on_open_selected_runner(self):
        runner_id = self._get_selected_runner_id()
        if runner_id is None:
            runner_id = self._get_selected_finished_runner_id()
        if runner_id is None:
            messagebox.showinfo("Open Runner", "Select a runner from the running, resting, or finished list.")
        else:
            self._open_runner_detail(runner_id)
          

    def _on_edit_timestamps(self):
        if self.edit_timestamp_uc is None:
            messagebox.showerror(
                "Review Workout",
                "Timestamp editing is not configured."
            )
            return

        workout = self.repo.get_by_id(self.workout_id) if self.repo else None
        if not workout or workout.status != WorkoutState.COMPLETED:
            messagebox.showinfo(
                "Review Workout",
                "Review & edit timestamps is only available after the workout has ended."
            )
            return

        # Post-workout the runner lives in the finished table; only fall
        # back to running/resting if the finished table has no selection.
        runner_id = self._get_selected_finished_runner_id()
        if runner_id is None:
            runner_id = self._get_selected_runner_id()
        if runner_id is None:
            messagebox.showinfo(
                "Review Workout",
                "Select a runner from the finished list to review their timestamps."
            )
            return

        runner_session = self._find_runner_session_in_workout(runner_id)
        if not runner_session:
            messagebox.showwarning(
                "Review Workout",
                "Could not find runner details for the selected athlete."
            )
            return

        TimestampEditorView(
            self.parent,
            self.edit_timestamp_uc,
            self.repo,
            self.workout_id,
            runner_session,
            undo_last_edit_uc=self.undo_last_edit_uc,
        )

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

    def _get_selected_finished_runner_id(self):
        """Parse a 'finished-{id}' iid out of the finished table selection."""
        selection = self.finished_tree.selection()
        if not selection:
            return None
        iid = selection[0]
        if not iid.startswith("finished-"):
            return None
        try:
            return int(iid.split("-", 1)[1])
        except ValueError:
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
            self.current_workout_id,
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
        if runner_id in self._auto_opened_runner_ids:
            return

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
            self.current_workout_id,
            scan_nfc_uc=self.nfc_uc,
            scan_rfid_uc=self.rfid_uc
        )
        runner_window.protocol("WM_DELETE_WINDOW", lambda w=runner_window: self._on_close_runner_window(w))
        self.runner_windows.append(runner_window)
        self._auto_opened_runner_ids.add(runner_id)

    def _find_runner_session_in_workout(self, runner_id: int):
        if not self.repo:
            return None
        workout = self.repo.get_by_id(self.current_workout_id)
        if not workout:
            return None

        for rs in workout.runnerSessions:
            if rs.runner.id == runner_id:
                return rs
        return None

    def _find_runner_session_by_tag(self, event_type: str, incoming_tag: str):
        """Find runner session by normalized NFC/RFID tag for state-aware scan handling."""
        if not self.repo:
            return None

        workout = self.repo.get_by_id(self.current_workout_id)
        if not workout:
            return None

        for rs in workout.runnerSessions:
            try:
                if event_type == "RFID":
                    if normalize_rfid_tag_id(rs.runner.rfid_tag) == incoming_tag:
                        return rs
                elif event_type == "NFC":
                    if normalize_nfc_tag_id(rs.runner.nfc_tag) == incoming_tag:
                        return rs
            except Exception:
                continue

        return None

    def _update_resting_table(self, views: List[RunnerRestView]):
        preserved_selection = self.resting_tree.selection()
        self.resting_tree.delete(*self.resting_tree.get_children())
        for v in views:
            runner_session = self._find_runner_session_in_workout(v.runner_id)
            if runner_session and self._is_runner_finished(runner_session):
                continue

            # Format remaining time nicely
            if v.remaining_rest_seconds > 0:
                minutes = v.remaining_rest_seconds // 60
                seconds = v.remaining_rest_seconds % 60
                time_display = f"{minutes}:{seconds:02d}"
            else:
                time_display = "Ready"
            
            status_display = "Ready" if v.is_ready_to_run else "Resting"
            next_action = "Scan to Run" if v.is_ready_to_run else f"Rest {time_display}"
            name_parts = v.runner_name.split()
            first_name = name_parts[0] if len(name_parts) > 0 else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            self.resting_tree.insert("", tk.END, iid=str(v.runner_id), values=(first_name, last_name, time_display, status_display, next_action))

        still_present = [iid for iid in preserved_selection if self.resting_tree.exists(iid)]
        if still_present:
            try:
                self.resting_tree.selection_set(still_present)
            except Exception:
                pass

    def _completed_intervals(self, runner_session) -> int:
        return sum(1 for interval in runner_session.intervals if interval.get("end"))

    def _total_laps(self, runner_session) -> int:
        return sum(len(interval.get("laps", [])) for interval in runner_session.intervals)

    def _is_runner_finished(self, runner_session) -> bool:
        return self._completed_intervals(runner_session) >= self.workout_target_intervals

    def _update_finished_table(self):
        preserved_selection = self.finished_tree.selection()
        self.finished_tree.delete(*self.finished_tree.get_children())

        if not self.repo:
            return

        workout = self.repo.get_by_id(self.current_workout_id)
        if not workout:
            return

        analytics_map = {}
        try:
            analytics = self.get_runner_analytics_uc.execute(self.current_workout_id)
            analytics_map = {a.runner_id: a for a in analytics}
        except Exception:
            analytics_map = {}

        for rs in workout.runnerSessions:
            if not self._is_runner_finished(rs):
                continue

            completed = self._completed_intervals(rs)
            total_laps = self._total_laps(rs)
            analytics_dto = analytics_map.get(rs.runner.id)
            pace_text = "N/A"
            if analytics_dto and analytics_dto.overall_avg_pace is not None:
                pace_text = f"{analytics_dto.overall_avg_pace:.1f}s/km"
            name_parts = rs.runner.name.split()
            first_name = name_parts[0] if len(name_parts) > 0 else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            self.finished_tree.insert(
                "",
                tk.END,
                iid=f"finished-{rs.runner.id}",
                values=(
                    first_name,
                    last_name,
                    f"{completed}/{self.workout_target_intervals}",
                    total_laps,
                    pace_text,
                    "Finished",
                ),
            )


        still_present = [iid for iid in preserved_selection if self.finished_tree.exists(iid)]
        if still_present:
            try:
                self.finished_tree.selection_set(still_present)
            except Exception:
                pass

    def _clear_charts(self):
        for w in self.chart_frame.winfo_children():
            w.destroy()
        for w in self.runner_detail_frame.winfo_children():
            w.destroy()
        for f in self.figures:
            try:
                plt.close(f)
            except:
                pass
        self.figures.clear()
        self.canvas_widgets.clear()

    def _clear_analytics_cache(self):
        self._cached_analytics_workout_id = None
        self._cached_runner_analytics = None
        self._cached_workout_stats = None

    def _get_analytics_data(self):
        if not self.repo:
            return [], None

        workout = self.repo.get_by_id(self.current_workout_id)
        if (
            workout
            and workout.status == WorkoutState.COMPLETED
            and self._cached_analytics_workout_id == self.current_workout_id
            and self._cached_runner_analytics is not None
            and self._cached_workout_stats is not None
        ):
            return self._cached_runner_analytics, self._cached_workout_stats

        analytics = self.get_runner_analytics_uc.execute(self.current_workout_id)
        stats = self.get_workout_stats_uc.execute(self.current_workout_id)

        if workout and workout.status == WorkoutState.COMPLETED:
            self._cached_analytics_workout_id = self.current_workout_id
            self._cached_runner_analytics = analytics
            self._cached_workout_stats = stats

        return analytics, stats

    def _render_runner_tabs(self, analytics):
        # Populate runner list (first/last name columns)
        self.runner_tree.delete(*self.runner_tree.get_children())
        self._runner_analytics_map = {}
        for runner in sorted(analytics, key=lambda a: a.runner_name):
            self.runner_tree.insert("", tk.END, iid=str(runner.runner_id), values=(runner.runner_name,))
            self._runner_analytics_map[str(runner.runner_id)] = runner
        # Clear detail view
        for w in self.runner_detail_frame.winfo_children():
            w.destroy()

    def _on_runner_selected(self, event):
        selected = self.runner_tree.selection()
        if not selected:
            return
        runner_id = selected[0]
        runner = self._runner_analytics_map.get(runner_id)
        if not runner:
            return
        # Clear previous detail widgets
        for w in self.runner_detail_frame.winfo_children():
            w.destroy()

        # Metrics summary
        pace_text = "N/A"
        if runner.overall_avg_pace is not None:
            pace_text = f"{runner.overall_avg_pace:.1f} s/km"
        ttk.Label(self.runner_detail_frame, text=f"Intervals: {len(runner.intervals)}   Avg Pace: {pace_text}", style="Body.TLabel").pack(anchor=tk.W, pady=(0, 8))

        # Pace trend chart
        if runner.intervals:
            fig = plot_pace_trend_for_single(runner)
            canvas = FigureCanvasTkAgg(fig, master=self.runner_detail_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.figures.append(fig)
            self.canvas_widgets.append(canvas)
        else:
            ttk.Label(self.runner_detail_frame, 
                      text="No interval data available for this runner.\n\n(The runner may not have started any intervals.)",
                      style="Caption.TLabel", justify="center").pack(pady=20, fill=tk.X)

        # Interval/split table
        table_frame = ttk.Frame(self.runner_detail_frame)
        table_frame.pack(fill=tk.X, pady=(12, 0))
        columns = ("interval", "duration", "pace", "splits")
        interval_table = ttk.Treeview(table_frame, columns=columns, show="headings", height=6)
        interval_table.heading("interval", text="Interval")
        interval_table.heading("duration", text="Duration (s)")
        interval_table.heading("pace", text="Pace (s/km)")
        interval_table.heading("splits", text="Splits (s)")
        interval_table.column("interval", width=70, anchor="center")
        interval_table.column("duration", width=100, anchor="center")
        interval_table.column("pace", width=100, anchor="center")
        interval_table.column("splits", width=200, anchor="w")
        for i in runner.intervals:
            duration_s = round(i.duration_ms / 1000.0, 2)
            pace = f"{i.pace_per_km:.2f}" if i.pace_per_km is not None else "--"
            splits = ", ".join(f"{s/1000.0:.2f}" for s in i.splits_ms) if i.splits_ms else "--"
            interval_table.insert("", tk.END, values=(i.interval_number, duration_s, pace, splits))
        interval_table.pack(fill=tk.X, expand=True)

        # Export button
        ttk.Button(self.runner_detail_frame, text="Export to PDF", command=lambda: self._export_runner_pdf(runner)).pack(anchor=tk.E, pady=(12, 0))

    def _export_runner_pdf(self, runner):
        # Export PDF for the selected runner only
        try:
            workout = self.repo.get_by_id(self.current_workout_id)
            if not workout:
                messagebox.showerror("Export Failed", "Workout not found.")
                return
            # Use the same PDF service as batch export, but filter to this runner
            # We'll use the report service directly for single-runner export
            from externalInterface.runner_pdf_report_service import RunnerPdfReportService
            pdf_service = RunnerPdfReportService()
            # Create a shallow copy of workout with only this runner's session
            class SingleRunnerWorkout:
                def __init__(self, base, session):
                    self.workout_id = base.workout_id  # Fixed: use workout_id
                    self.intervalDistance = base.intervalDistance
                    self.startTime = getattr(base, 'startTime', None)
                    self.endTime = getattr(base, 'endTime', None)
                    self.runnerSessions = [session]
            # Find the session for this runner
            session = next((s for s in workout.runnerSessions if s.runner.id == runner.runner_id), None)
            if not session:
                messagebox.showerror("Export Failed", f"Runner session not found for {runner.runner_name}.")
                return
            single_workout = SingleRunnerWorkout(workout, session)
            files = pdf_service.generate_reports_for_workout(single_workout)
            if files:
                messagebox.showinfo("Export Complete", f"PDF exported to:\n{files[0]}")
            else:
                messagebox.showerror("Export Failed", "No PDF file was generated.")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Error: {e}")

    def _build_analytics_signature(self, analytics, stats):
        def _runner_signature(a: RunnerAnalyticsDTO):
            intervals = tuple(
                (
                    i.interval_number,
                    i.duration_ms,
                    round(i.pace_per_km, 3) if i.pace_per_km is not None else None,
                    tuple(i.splits_ms),
                )
                for i in a.intervals
            )
            return (
                a.runner_id,
                a.runner_name,
                round(a.overall_avg_pace, 3) if a.overall_avg_pace is not None else None,
                round(a.rest_efficiency, 3) if a.rest_efficiency is not None else None,
                intervals,
            )

        runners_sig = tuple(sorted((_runner_signature(a) for a in analytics), key=lambda r: r[0]))
        return (
            stats.total_runners,
            stats.intervals_completed,
            runners_sig,
        )

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
            # Use the application layer use case instead of direct external interface calls
            added_runners = self.load_roster_uc.execute(
                self.current_workout_id,
                file_path,
                default_rest_duration=self.default_rest_duration,
            )
            
            workout = self.repo.get_by_id(self.current_workout_id)
            self.workout_active = workout.status == WorkoutState.ACTIVE
            self.btn_start.config(state=tk.NORMAL, text="▶ Start Workout")
            self.btn_end.config(state=tk.DISABLED, text="⏹ End Workout")
            self._clear_analytics_cache()

            # Save as last known roster
            runners = [session.runner for session in workout.runnerSessions]
            self.last_roster_service.save_roster(runners)

            # Refresh UI and show success message
            self._poll()
            messagebox.showinfo("Success", f"Loaded {len(added_runners)} athletes")
            self._update_status_badge(f"✓ {len(added_runners)} runners", ModernTheme.SUCCESS)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load roster: {str(e)}")
            self._update_status_badge("Load Failed", ModernTheme.DANGER)

    def _on_toggle_chart(self):
        # Jump to analytics tab and refresh pace analytics.
        self.notebook.select(self.analytics_frame)
        self._update_analytics(force=True)

    def _on_start_workout(self):
        try:
            if not self.start_workout_uc:
                raise RuntimeError("Start workout use case is not configured.")

            if not self.repo:
                raise RuntimeError("Workout repository is not available.")

            workout = self.repo.get_by_id(self.current_workout_id)
            if workout is None:
                raise RuntimeError(f"Workout #{self.current_workout_id} is not loaded.")

            if workout.status != WorkoutState.NOT_STARTED:
                raise RuntimeError(f"Workout cannot start because it is already {workout.status.value.replace('_', ' ').lower()}.")

            if not getattr(workout, 'runnerSessions', None):
                raise RuntimeError("No runners are loaded. Load a roster before starting the workout.")

            # Provide immediate feedback
            self._flash_status_message("Starting workout...", ModernTheme.PRIMARY)
            self.btn_start.config(state=tk.DISABLED, text="⏳ Starting...")

            started = self.start_workout_uc.execute(self.current_workout_id)
            if not started:
                raise RuntimeError("Workout start was blocked by the current workout state.")
            if workout.startMode.upper() == "GROUP" and self.group_start_uc:
                try:
                    ready, active, resting = self.group_start_uc.execute(self.current_workout_id)
                    self._flash_status_message(f"Group start: {ready} runners started", ModernTheme.SUCCESS, 3000)
                    # Force immediate refresh of running table
                    self._poll()
                    # Also force the running tree to rebuild now
                    self.update_idletasks()
                except Exception as e:
                    self._flash_status_message(f"Group start error: {str(e)}", ModernTheme.WARNING, 3000)

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
        if not messagebox.askyesno("End Workout",
                                   "Are you sure you want to end the workout?\n\nThis will stop all runners and finalize the session.",
                                   icon='warning'):
            return

        try:
            if self.end_workout_uc:
                self._flash_status_message("Ending workout...", ModernTheme.WARNING)
                self.btn_end.config(state=tk.DISABLED, text="⏳ Ending...")

                self.end_workout_uc.execute(self.current_workout_id)
                self.workout_active = False
                self._clear_analytics_cache()
                try:
                    self._cached_runner_analytics, self._cached_workout_stats = self._get_analytics_data()
                    self._cached_analytics_workout_id = self.current_workout_id
                except Exception:
                    self._clear_analytics_cache()

                # --- Prompt for workout name and save full summary ---
                workout_name = simpledialog.askstring(
                    "Save Workout",
                    "Enter a name for this workout session:",
                    parent=self.parent
                )
                if not workout_name:
                    workout_name = f"Workout_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                summary_dict = self._build_workout_summary_dict(workout_name)
                try:
                    save_workout_summary(str(self.current_workout_id), summary_dict)
                    self._flash_status_message(f"Workout saved as '{workout_name}'", ModernTheme.SUCCESS)
                except StorageThresholdWarning as warn:
                    messagebox.showwarning("Storage Limit Warning", str(warn))
                except Exception as e:
                    messagebox.showerror("Save Error", f"Failed to save workout summary: {e}")
                
                # --- Ask user where to export a copy of the JSON ---
              

                default_json_name = f"{workout_name}.json"
                json_path = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                    initialfile=default_json_name,
                    title="Export JSON (raw workout data) – optional, click Cancel to skip"
                )
                if json_path:
                    try:
                        with open(json_path, "w", encoding="utf-8") as f:
                            json.dump(summary_dict, f, indent=2)
                        self._flash_status_message(f"JSON exported to {Path(json_path).name}", ModernTheme.SUCCESS, 3000)
                    except Exception as e:
                        messagebox.showerror("Export Error", f"Failed to export JSON:\n{e}")
                else:
                    self._flash_status_message("JSON export skipped", ModernTheme.WARNING, 2000)


                # --- Ask user where to save the PDF summary ---
                pdf_gen = WorkoutSummaryPdfGenerator()
                default_pdf_name = f"{workout_name}.pdf"
                pdf_path = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                    initialfile=default_pdf_name,
                    title="Save PDF (readable summary) – optional, click Cancel to skip"
                )
                if pdf_path:
                    try:
                        pdf_gen.generate(summary_dict, Path(pdf_path))
                        self._flash_status_message(f"PDF saved to {Path(pdf_path).name}", ModernTheme.SUCCESS, 3000)
                    except Exception as pdf_err:
                        messagebox.showerror("PDF Error", f"Failed to save PDF:\n{pdf_err}")
                else:
                    self._flash_status_message("PDF export skipped", ModernTheme.WARNING, 2000)

                # Update button states
                self.btn_start.config(state=tk.NORMAL, text="▶ Start Workout")
                self.btn_end.config(state=tk.DISABLED, text="⏹ End Workout")
                self._update_status_badge("⏹ Completed", ModernTheme.PRIMARY)
                self._flash_status_message("Workout ended successfully!", ModernTheme.SUCCESS)

        except Exception as e:
            self.btn_end.config(state=tk.NORMAL, text="⏹ End Workout")
            self._update_status_badge("❌ End Failed", ModernTheme.DANGER)
            self._flash_status_message(f"Failed to end workout: {str(e)}", ModernTheme.DANGER)

    def _on_export(self):
        try:
            stats = self.get_workout_stats_uc.execute(self.current_workout_id)
            analytics = self.get_runner_analytics_uc.execute(self.current_workout_id)

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

    def _update_analytics(self, force: bool = False):
        # Avoid frequent full redraws that can appear glitchy.
        if not force:
            if self.notebook.select() != str(self.analytics_frame):
                return
            now = time.time()
            if (now - self.last_analytics_update_at) < self.analytics_min_refresh_seconds:
                return
            self.last_analytics_update_at = now

        try:
            analytics, stats = self._get_analytics_data()
        except Exception:
            return

        if stats is None:
            return

        signature = self._build_analytics_signature(analytics, stats)
        if not force and signature == self.last_analytics_signature:
            return
        self.last_analytics_signature = signature

        self._clear_charts()
        self.stats_label.config(
            text=(
                f"Runners: {stats.total_runners} | Intervals: {stats.intervals_completed} | "
                f"View: {len(analytics)} | Mode: pace"
            )
        )

        if not analytics:
            empty_message = "No pace analytics available"
            ttk.Label(self.chart_frame, text=empty_message, style="Status.TLabel").pack(pady=40)
            return

        fig = plot_pace_trend(analytics)

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.chart_frame.update_idletasks()
        self.figures.append(fig)
        self.canvas_widgets.append(canvas)

        self._render_runner_tabs(analytics)

    def _on_save_last_roster(self):
        """Save current roster as the last known roster."""
        try:
            if not self.repo:
                messagebox.showerror("Error", "Repository not available")
                return

            workout = self.repo.get_by_id(self.current_workout_id)
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

            workout = self.repo.get_by_id(self.current_workout_id)
            if not workout:
                from domain.workout import Workout
                workout = Workout(workout_id=self.current_workout_id, intervalDistance=400, lapsPerInterval=1, startMode="INDIVIDUAL")
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
            self._clear_analytics_cache()

            # Refresh UI and show success message
            self._poll()
            messagebox.showinfo("Success", f"Loaded {len(runners)} runners from saved roster")
            self._update_status_badge(f"✓ {len(runners)} runners", ModernTheme.SUCCESS)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load roster: {str(e)}")
            self._update_status_badge("Load Failed", ModernTheme.DANGER)

    def _on_generate_pdf_reports(self):
        """Generate PDF reports for all runners – user chooses output folder."""
        try:
            if not self.generate_report_uc:
                messagebox.showerror("Error", "Report generation is not configured")
                return

            if not self.repo:
                messagebox.showerror("Error", "Repository not available")
                return

            workout = self.repo.get_by_id(self.current_workout_id)
            if not workout:
                messagebox.showerror("Error", "No workout loaded")
                return

            if workout.status != WorkoutState.COMPLETED:
                result = messagebox.askyesno("Warning", 
                    "Workout is not completed. Generate reports anyway?", 
                    icon='warning')
                if not result:
                    return

            # Ask user for output directory
            output_dir = filedialog.askdirectory(
                title="Select Folder to Save PDF Reports"
            )
            if not output_dir:
                self._flash_status_message("PDF generation cancelled", ModernTheme.WARNING, 2000)
                return

            generated_files = self.generate_report_uc.execute(workout, output_dir=Path(output_dir))
            
            if generated_files:
                messagebox.showinfo("Success", 
                    f"Generated {len(generated_files)} PDF reports in:\n{output_dir}")
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

    def _stop_scanning(self):
        """Stop active scanner adapters and restore UI state."""
        self._cleanup_adapters()
        self.scanning_active = False
        if self.scan_button:
            self.scan_button.config(text="📡 Start Scanning")
        self._update_status_badge("Standby", ModernTheme.WARNING)

    def _cleanup_adapters(self):
        """Best-effort shutdown for scanner adapters."""
        for adapter_attr in ("rfid_adapter", "nfc_adapter"):
            adapter = getattr(self, adapter_attr, None)
            if adapter is None:
                continue
            try:
                adapter.stop()
            except Exception:
                pass
            setattr(self, adapter_attr, None)

    def _start_scanning(self):
        """Initialize and start hardware scanning."""
        try:
            # Initialize RFID adapter (you may need to configure the scanner address)
            rfid_scanner_address = "http://localhost:5001/"  # Simulation server (or real Impinj REST endpoint)
            self.rfid_adapter = create_rfid_rest_adapter(rfid_scanner_address)
            
            # Initialize NFC adapter; in simulator mode prefer roster tags for deterministic matching.
            workout = self.repo.get_by_id(self.current_workout_id) if self.repo else None
            roster_nfc_tags = []
            if workout:
                roster_nfc_tags = [rs.runner.nfc_tag for rs in workout.runnerSessions if getattr(rs.runner, "nfc_tag", None)]
            self.nfc_adapter = create_nfc_adapter(tags=roster_nfc_tags)
            
            # Set up event callbacks
            self.rfid_adapter.set_event_callback(self._on_scanner_event)
            self.nfc_adapter.set_event_callback(self._on_scanner_event)
            
            # Start adapters
            self.rfid_adapter.start()
            self.nfc_adapter.start()
            
            self.scanning_active = True
            self._update_status_badge("🔍 Scanning", ModernTheme.PRIMARY)
            
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

    def _on_scanner_event(self, payload: ScannerPayload):
        """Handle scanner events from hardware."""
        try:
            timestamp_str = datetime.fromtimestamp(payload.timestamp_ms / 1000).isoformat()
            workout = self.repo.get_by_id(self.current_workout_id) if self.repo else None

            if not workout or workout.status != WorkoutState.ACTIVE:
                return
            
            if payload.event_type == "RFID":
                if self.rfid_uc:
                    normalized_tag = normalize_rfid_tag_id(payload.tag_id)
                    session = self._find_runner_session_by_tag("RFID", normalized_tag)
                    if not session or session.state != RunnerState.RUNNING:
                        return

                    if self._is_runner_finished(session):
                        return

                    result = self.rfid_uc.execute(self.current_workout_id, normalized_tag, timestamp_str, use_event_time=True)
                    if result.decision.value == "ACCEPTED":
                        self.after(0, lambda: self._flash_status_message(f"RFID: {normalized_tag[:8]}...", ModernTheme.SUCCESS, 1000))
                    else:
                        self.after(0, lambda: self._flash_status_message(f"RFID rejected: {result.reason.value}", ModernTheme.WARNING, 1500))
                        
            elif payload.event_type == "NFC":
                if self.nfc_uc:
                    normalized_tag = normalize_nfc_tag_id(payload.tag_id)
                    session = self._find_runner_session_by_tag("NFC", normalized_tag)
                    if not session:
                        return

                    if self._is_runner_finished(session):
                        return

                    # Simulate realistic start timing: only start when not running.
                    if session.state == RunnerState.RUNNING:
                        return

                    self.nfc_uc.execute(self.current_workout_id, normalized_tag, timestamp_str, use_event_time=True)
                    self.after(0, lambda: self._flash_status_message(f"NFC: {normalized_tag[:8]}...", ModernTheme.SUCCESS, 1000))
                    
            # Refresh the UI to show updated status
            self.after(500, self._poll)
            
        except Exception as e:
            if self._is_expected_scanner_error(e):
                return
            print(f"Error processing scanner event: {e}")
            self.after(0, lambda: self._flash_status_message("Scan Error", ModernTheme.DANGER, 2000))

    def _is_expected_scanner_error(self, error: Exception) -> bool:
        """Suppress expected state-transition errors during simulation streams."""
        message = str(error)
        expected = (
            "Runner is already running",
            "Cannot record lap unless runner is running",
            "Workout is not active",
        )
        return any(fragment in message for fragment in expected)

    def _on_window_close(self):
        """Handle window close event with proper cleanup."""
        self._stop_scanning()
        self.parent.destroy()

    def _build_workout_summary_dict(self, workout_name: str) -> dict:
        """Build a complete summary dict with config, roster, and results."""
        workout = self.repo.get_by_id(self.current_workout_id)
        if not workout:
            return {}

        # --- Configuration ---
        config = {
            "interval_distance_m": workout.intervalDistance,
            "laps_per_interval": workout.lapsPerInterval,
            "start_mode": workout.startMode,
            "default_rest_seconds": self.default_rest_duration,
            "target_intervals": self.workout_target_intervals,
        }

        # --- Roster (list of runners with their tags) ---
        roster = []
        for rs in workout.runnerSessions:
            roster.append({
                "id": rs.runner.id,
                "name": rs.runner.name,
                "rfid_tag": rs.runner.rfid_tag,
                "nfc_tag": rs.runner.nfc_tag,
            })

        # --- Results (from analytics DTO) ---
        analytics_list, _ = self._get_analytics_data()  # returns List[RunnerAnalyticsDTO]
        results = {}
        for a in analytics_list:
            results[str(a.runner_id)] = {
                "intervals": [
                    {
                        "number": i.interval_number,
                        "duration_ms": i.duration_ms,
                        "pace_per_km": i.pace_per_km,
                        "splits_ms": i.splits_ms,
                    }
                    for i in a.intervals
                ],
                "overall_avg_pace_s_per_km": a.overall_avg_pace,
                "rest_efficiency": a.rest_efficiency,
            }

        # --- Global metrics (simple) ---
        total_runners = len(roster)
        completed_intervals = sum(len(r["intervals"]) for r in results.values())

        return {
            "name": workout_name,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "config": config,
            "roster": roster,
            "results": results,
            "global_metrics": {
                "total_runners": total_runners,
                "total_completed_intervals": completed_intervals,
            },
        }


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
