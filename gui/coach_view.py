import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from typing import List, Optional
import os

from tomlkit import datetime

from ..application.dto.runner_rest_view import RunnerRestView
from ..application.dto.runner_running_view import RunnerRunningView
from ..application.dto.runner_analytics_dto import RunnerAnalyticsDTO
from ..application.dto.workout_stats_dto import WorkoutStatsDTO
from gui.analytics_widgets import plot_pace_trend, plot_split_distribution
from gui.utils import show_error_dialog, show_info_dialog


class CoachView(ttk.Frame):
    """
    Coach GUI window displaying real-time workout data and analytics.
    """

    def __init__(
        self,
        parent,
        repository,
        get_rest_uc,
        get_running_uc,
        get_runner_analytics_uc,
        get_workout_stats_uc,
        start_workout_uc,
        end_workout_uc,
        group_start_uc,
        scan_nfc_uc,
        scan_rfid_uc,
        add_runner_uc,
        csv_parser,
        workout_id: int,
        refresh_interval_ms: int = 1000,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.repository = repository
        self.get_rest_uc = get_rest_uc
        self.get_running_uc = get_running_uc
        self.get_runner_analytics_uc = get_runner_analytics_uc
        self.get_workout_stats_uc = get_workout_stats_uc
        self.start_workout_uc = start_workout_uc
        self.end_workout_uc = end_workout_uc
        self.group_start_uc = group_start_uc
        self.scan_nfc_uc = scan_nfc_uc
        self.scan_rfid_uc = scan_rfid_uc
        self.add_runner_uc = add_runner_uc
        self.csv_parser = csv_parser
        self.workout_id = workout_id
        self.refresh_interval_ms = refresh_interval_ms

        self._setup_styles()
        self._setup_ui()
        self._start_polling()

    def _setup_styles(self):
        """Configure ttk styles for a modern look."""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#F5F5F5')
        style.configure('TLabel', background='#F5F5F5', font=('Helvetica', 11))
        style.configure('TButton', font=('Helvetica', 11), padding=6)
        style.configure('TNotebook', background='#F5F5F5')
        style.configure('TNotebook.Tab', font=('Helvetica', 11), padding=[12, 4])
        style.configure('Treeview', font=('Helvetica', 10), rowheight=28)
        style.configure('Treeview.Heading', font=('Helvetica', 11, 'bold'))
        style.map('Treeview', background=[('selected', '#E5E5E5')])

    def _setup_ui(self):
        """Create the UI widgets."""
        self.parent.title("Coach View - Interval Workout Manager")
        self.parent.geometry("1200x800")
        self.parent.minsize(900, 600)

        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        # Buttons
        ttk.Button(toolbar, text="Load Athletes CSV", command=self.load_athletes_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Load Events CSV", command=self.load_events_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Group Start", command=self.group_start).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Simulate NFC", command=self.simulate_nfc).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Simulate RFID", command=self.simulate_rfid).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="End Workout", command=self.end_workout).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Refresh Now", command=self._poll).pack(side=tk.LEFT, padx=2)

        # Separator
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=5)

        # Notebook (tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Live status
        self.live_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.live_frame, text="Live Status")

        # Split panes for live status
        paned = ttk.PanedWindow(self.live_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Running athletes pane
        running_frame = ttk.LabelFrame(paned, text="Running Athletes")
        paned.add(running_frame, weight=1)
        self.running_tree = ttk.Treeview(
            running_frame,
            columns=("name", "interval", "laps", "progress"),
            show="headings",
            height=8
        )
        self.running_tree.heading("name", text="Name")
        self.running_tree.heading("interval", text="Interval")
        self.running_tree.heading("laps", text="Laps")
        self.running_tree.heading("progress", text="Progress")
        self.running_tree.column("name", width=150)
        self.running_tree.column("interval", width=80)
        self.running_tree.column("laps", width=80)
        self.running_tree.column("progress", width=150)
        self.running_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Resting athletes pane
        resting_frame = ttk.LabelFrame(paned, text="Resting Athletes")
        paned.add(resting_frame, weight=1)
        self.resting_tree = ttk.Treeview(
            resting_frame,
            columns=("name", "remaining", "ready"),
            show="headings",
            height=8
        )
        self.resting_tree.heading("name", text="Name")
        self.resting_tree.heading("remaining", text="Remaining Rest (s)")
        self.resting_tree.heading("ready", text="Ready")
        self.resting_tree.column("name", width=150)
        self.resting_tree.column("remaining", width=120)
        self.resting_tree.column("ready", width=80)
        self.resting_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 2: Analytics
        self.analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_frame, text="Analytics")

        # Charts container (scrollable if needed)
        canvas_frame = ttk.Frame(self.analytics_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.chart_canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.chart_canvas.yview)
        self.chart_scroll_frame = ttk.Frame(self.chart_canvas)
        self.chart_canvas.create_window((0, 0), window=self.chart_scroll_frame, anchor=tk.NW)
        self.chart_canvas.configure(yscrollcommand=scrollbar.set)
        self.chart_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chart_scroll_frame.bind("<Configure>", lambda e: self.chart_canvas.configure(scrollregion=self.chart_canvas.bbox("all")))

        # Placeholder for figures
        self.figures = []

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
            # Silently ignore if method missing (will be fixed soon)
            pass

        try:
            resting_views = self.get_rest_uc.execute(self.workout_id)
            self._update_resting_table(resting_views)
        except Exception as e:
            pass

        # Update analytics charts (only if new data)
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

    def _update_analytics(self):
        """Update charts with fresh analytics data."""
        try:
            runner_analytics = self.get_runner_analytics_uc.execute(self.workout_id)
            workout_stats = self.get_workout_stats_uc.execute(self.workout_id)
        except Exception as e:
            # If analytics not available (e.g., no intervals), skip
            return

        # Clear previous figures
        for fig in self.figures:
            fig.clear()
        self.figures.clear()

        # Clear the scroll frame
        for widget in self.chart_scroll_frame.winfo_children():
            widget.destroy()

        # Create pace trend figure
        pace_fig = plot_pace_trend(runner_analytics)
        canvas = FigureCanvasTkAgg(pace_fig, master=self.chart_scroll_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.X, expand=False, pady=5)
        self.figures.append(pace_fig)

        # Add more charts as needed
        # e.g., split distribution for selected runner, etc.

    # ---------------------------
    # Action methods
    # ---------------------------

    def load_athletes_csv(self):
        """Load athletes from CSV file."""
        file_path = filedialog.askopenfilename(
            title="Select athletes.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            return
        try:
            # Use the CSV parser to load roster data
            roster_data = self.csv_parser.parse_csv_file(file_path)
            # Validate unique tags
            ok, errors = self.csv_parser.validate_unique_tags(roster_data)
            if not ok:
                messagebox.showerror("Validation Error", "\n".join(errors))
                return

            # Get workout
            workout = self.repository.get_by_id(self.workout_id)
            if not workout:
                messagebox.showerror("Error", "Workout not found")
                return

            # Add each runner
            from domain.runner import Runner
            from domain.runnerSession import RunnerSession
            added = 0
            for data in roster_data:
                runner = Runner(
                    runner_id=len(workout.runnerSessions) + added + 1,
                    name=data.name,
                    email=data.email or "",
                    nfc_tag=data.nfc_id,
                    rfid_tag=data.rfid_id
                )
                session = RunnerSession(
                    runner=runner,
                    restDuration=60  # default rest duration
                )
                if workout.add_runner_session(session):
                    added += 1
            self.repository.save(workout)
            messagebox.showinfo("Success", f"Loaded {added} athletes.")
            self._poll()  # refresh immediately
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV: {e}")

    def load_events_csv(self):
        """Load and replay events.csv."""
        file_path = filedialog.askopenfilename(
            title="Select events.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            return
        # Reuse the EventCSVProcessor from the controller layer
        from controller.cli import EventCSVProcessor
        processor = EventCSVProcessor(self)  # we need a CLI-like object
        # This requires that we have a wrapper that mimics the CLI's methods.
        # For now, we'll implement a minimal stub or use the CLI directly.
        # Simpler: we can call the CLI's event processor but that expects a CLI instance.
        # Alternatively, we can reimplement the logic here. Since we have use cases,
        # we can parse events and call the appropriate use cases.
        self._replay_events_from_csv(file_path)

    def _replay_events_from_csv(self, file_path):
        """Parse and replay events.csv using use cases."""
        import csv
        from datetime import datetime
        from application.exceptions import WorkoutNotFoundError

        events = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    etype = row.get('TYPE', '').strip().upper()
                    timestamp_str = row.get('TIMESTAMP', '').strip()
                    tag = row.get('TAG', '').strip()
                    if not etype or not timestamp_str:
                        continue
                    try:
                        timestamp_ms = int(timestamp_str)
                        dt = datetime.fromtimestamp(timestamp_ms / 1000.0)
                    except:
                        continue
                    events.append((etype, dt, tag))
            # Sort by timestamp
            events.sort(key=lambda x: x[1])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse events file: {e}")
            return

        # Process each event
        group_nfc_tags = []
        for etype, dt, tag in events:
            try:
                if etype == 'GROUP':
                    if tag:
                        group_nfc_tags.append(tag)
                elif etype == 'START':
                    if group_nfc_tags:
                        self.group_start_uc.execute(self.workout_id, group_nfc_tags)
                        group_nfc_tags.clear()
                elif etype == 'NFC' and tag:
                    self.scan_nfc_uc.execute(self.workout_id, tag, dt.isoformat(), use_event_time=True)
                elif etype == 'RFID' and tag:
                    self.scan_rfid_uc.execute(self.workout_id, tag, dt.isoformat(), use_event_time=True)
            except Exception as e:
                print(f"Error processing event {etype}: {e}")
        messagebox.showinfo("Replay Complete", f"Processed {len(events)} events.")

    def group_start(self):
        """Trigger group start for runners added to group."""
        # For simplicity, we could allow selecting runners from a list.
        # For now, just start with all NOT_STARTED runners (like CLI's group start with no tags)
        try:
            ready, active, resting = self.group_start_uc.execute(self.workout_id)
            messagebox.showinfo("Group Start", f"Prepared {ready} runners.\nActive: {active}, Resting: {resting}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def simulate_nfc(self):
        """Simulate NFC scan for a runner."""
        # Ask for NFC tag
        tag = self._ask_tag("Enter NFC tag to simulate:", "NFC Scan")
        if not tag:
            return
        try:
            timestamp = datetime.now().isoformat()
            status = self.scan_nfc_uc.execute(self.workout_id, tag, timestamp, use_event_time=False)
            messagebox.showinfo("NFC Scan", f"NFC scan for tag {tag} processed.\nActive: {status.active_runner_count}, Resting: {status.resting_runner_count}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def simulate_rfid(self):
        """Simulate RFID detection."""
        tag = self._ask_tag("Enter RFID tag to simulate:", "RFID Detection")
        if not tag:
            return
        try:
            timestamp = datetime.now().isoformat()
            result = self.scan_rfid_uc.execute(self.workout_id, tag, timestamp, use_event_time=False)
            messagebox.showinfo("RFID Detection", f"RFID detection for tag {tag} processed.\nDecision: {result.decision}\nReason: {result.reason}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def end_workout(self):
        """End the current workout."""
        try:
            ended = self.end_workout_uc.execute(self.workout_id)
            if ended:
                messagebox.showinfo("Workout Ended", "Workout has been ended successfully.")
            else:
                messagebox.showwarning("Workout End", "Workout could not be ended.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _ask_tag(self, prompt, title):
        """Ask for a tag via simple dialog."""
        from tkinter.simpledialog import askstring
        return askstring(title, prompt)