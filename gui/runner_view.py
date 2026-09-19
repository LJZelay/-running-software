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
        runner,
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
        self.runner = runner
        self.runner_id = runner.id
        self.workout_id = workout_id
        self.refresh_interval_ms = refresh_interval_ms
        self.lap_count = 0

        self.title("Runner Dashboard")
        self.geometry("700x600")
        ModernTheme.configure(self)
        self._setup_ui()
        self._start_polling()

    def _setup_ui(self):
        """Create UI following Apple's design principles."""
        self.title(f"Runner - {self.runner.name}")
        self.geometry("700x600")
        ModernTheme.configure(self)

        # Header with runner name
        header_frame = ttk.Frame(self, style="GlassHighlight.TFrame")
        header_frame.pack(fill=tk.X, side=tk.TOP)

        ttk.Label(header_frame, text=f"🏃 {self.runner.name}", style="Title.TLabel").pack(side=tk.LEFT, padx=(16, 0), pady=(12, 6))

        # Action buttons with proper hierarchy
        btn_frame = ttk.Frame(self, style="GlassHighlight.TFrame")
        btn_frame.pack(fill=tk.X, pady=(8, 16))

        ttk.Button(btn_frame, text="🏃 Record Lap",
                  command=self._simulate_lap, style="Success.TButton").pack(side=tk.LEFT, padx=(16, 8))
        ttk.Button(btn_frame, text="📞 Request Coach",
                  command=self._request_coach, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="🔄 Refresh",
                  command=self._refresh, style="Secondary.TButton").pack(side=tk.LEFT)
        
        # Create Notebook (tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        # Main content with glass-style styling
        self.main = ttk.Frame(self, style="Glass.TFrame", padding=(20, 16))
        self.main.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        # Status section
        ttk.Label(self.main, text="Current Status", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 8))
        self.status = ttk.Label(self.main, text="Ready", style="Body.TLabel")
        self.status.pack(anchor=tk.W, pady=(0, 16))

        # Stats grid
        stats_frame = ttk.Frame(self.main, style="GlassHighlight.TFrame", padding=(16, 12))
        stats_frame.pack(fill=tk.X, pady=(0, 16))

        # Rest timer
        ttk.Label(stats_frame, text="Rest Timer", style="Subheader.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.timer = ttk.Label(stats_frame, text="-- s", style="Body.TLabel")
        self.timer.grid(row=1, column=0, sticky="w", pady=(0, 12))

        # Lap count
        ttk.Label(stats_frame, text="Laps Completed", style="Subheader.TLabel").grid(row=0, column=1, sticky="w", padx=(24, 0), pady=(0, 4))
        self.lap_label = ttk.Label(stats_frame, text=f"{self.lap_count}", style="Body.TLabel")
        self.lap_label.grid(row=1, column=1, sticky="w", padx=(24, 0))

        # Average Pace Label
        ttk.Label(stats_frame, text="Average Pace", style="Subheader.TLabel").grid(row=0, column=2, sticky="w", padx=(24, 0), pady=(0, 4))
        self.pace_label = ttk.Label(stats_frame, text="-- s/km", style="Body.TLabel")
        self.pace_label.grid(row=1, column=2, sticky="w", padx=(24, 0))

        # NEW: Interval progress (optional)
        ttk.Label(stats_frame, text="Intervals Done", style="Subheader.TLabel").grid(row=0, column=3, sticky="w", padx=(24, 0), pady=(0, 4))
        self.interval_label = ttk.Label(stats_frame, text="0", style="Body.TLabel")
        self.interval_label.grid(row=1, column=3, sticky="w", padx=(24, 0))

        # Feedback message
        self.feedback = ttk.Label(self.main, text="Ready for action", style="Caption.TLabel", wraplength=500)
        self.feedback.pack(anchor=tk.W, pady=(0, 16))

        # Chart section
        ttk.Label(self.main, text="Pace Trend", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 8))
        self.chart_frame = ttk.Frame(self.main, style="GlassHighlight.TFrame", padding=(16, 12))
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

        self.fig = None
        self.canvas = None

         # ==================== TAB 2: Profile ====================
        self.profile_frame = ttk.Frame(self.notebook, style="Glass.TFrame", padding=(20, 16))
        self.notebook.add(self.profile_frame, text="👤 Profile")

        def add_profile_row(parent, label_text, value_text, row):
            ttk.Label(parent, text=label_text, style="Subheader.TLabel").grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))
            ttk.Label(parent, text=value_text, style="Body.TLabel").grid(row=row, column=1, sticky="w", pady=6)

        # Full name
        add_profile_row(self.profile_frame, "Full Name:", self.runner.name, 0)

        # Email
        email = getattr(self.runner, 'email', 'N/A')
        if not email or email.strip() == "":
            email = "Not provided"
        add_profile_row(self.profile_frame, "Email:", email, 1)

        # Address – not in domain yet
        address = getattr(self.runner, 'address', None)
        if address is None:
            address = "Not available (add 'address' field to Runner)"
        elif not address.strip():
            address = "Not provided"
        add_profile_row(self.profile_frame, "Address:", address, 2)

        # RFID tag
        rfid = getattr(self.runner, 'rfid_tag', 'N/A')
        if not rfid or rfid.strip() == "":
            rfid = "Not assigned"
        add_profile_row(self.profile_frame, "RFID Tag:", rfid, 3)

        # NFC tag
        nfc = getattr(self.runner, 'nfc_tag', 'N/A')
        if not nfc or nfc.strip() == "":
            nfc = "Not assigned"
        add_profile_row(self.profile_frame, "NFC Tag:", nfc, 4)

        ttk.Label(self.profile_frame, text="ℹ️ Contact info can be updated in the roster CSV.", style="Caption.TLabel").grid(row=5, column=0, columnspan=2, sticky="w", pady=(20, 0))

    def _start_polling(self):
        self._poll()
        self.after(self.refresh_interval_ms, self._start_polling)

    def _poll(self):
        try:
            rest_views = self.get_rest_uc.execute(self.workout_id)
            my_rest = next((v for v in rest_views if v.runner_id == self.runner_id), None)
            if my_rest:
                self.timer.config(text=f"{my_rest.remaining_rest_seconds} s")
                ready_label = "Ready!" if my_rest.is_ready_to_run else "Wait..."
                self.status.config(text=f"Resting - {ready_label}")
            else:
                self.status.config(text="Running")
        except:
            pass

        try:
            analytics = self.get_runner_analytics_uc.execute(self.workout_id)
            my_analytics = next((a for a in analytics if a.runner_id == self.runner_id), None)
            if my_analytics:
                # MODIFIED: Compute total laps from all intervals
                total_laps = sum(len(interval.splits_ms) for interval in my_analytics.intervals)
                self.lap_label.config(text=str(total_laps))
                # Update intervals done
                intervals_done = len(my_analytics.intervals)
                self.interval_label.config(text=str(intervals_done))
                # Update average pace
                avg_pace = my_analytics.overall_avg_pace
                if avg_pace is not None:
                    self.pace_label.config(text=f"{avg_pace:.1f}")
                else:
                    self.pace_label.config(text="--")

                # Update chart
                if self.fig is None:
                    self.fig = plot_pace_trend_for_single(my_analytics)
                    self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
                    self.canvas.draw()
                    self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                else:
                    self.fig.clear()
                    self.fig = plot_pace_trend_for_single(my_analytics, fig=self.fig)
                    self.canvas.draw()
            else:
                # No analytics yet – reset display
                self.lap_label.config(text="0")
                self.interval_label.config(text="0")
                self.pace_label.config(text="--")
        except Exception as e:
            # Silently ignore; avoid spamming console
            pass
                

    def _simulate_lap(self):
        """Record a lap with visual feedback following Apple's feedback principle."""
        try:
            if self.scan_rfid_uc and self.runner.rfid_tag:
                self.scan_rfid_uc.execute(
                    self.workout_id,
                    self.runner.rfid_tag,
                    datetime.now().isoformat()
                )
                # MODIFIED: Do NOT increment lap count manually – rely on next poll to update based on actual data
            self.feedback.config(text=f"Lap recorded at {datetime.now().strftime('%H:%M:%S')}", style="Body.TLabel")
            # Visual feedback - temporarily highlight the lap label
            self._flash_feedback(self.lap_label, ModernTheme.SUCCESS)
        except Exception as e:
            self.feedback.config(text=f"Error: {str(e)[:40]}", style="Caption.TLabel")
            self._flash_feedback(self.feedback, ModernTheme.DANGER)

    def _flash_feedback(self, widget, color):
        """Provide visual feedback by briefly changing widget color."""
        original_bg = widget.cget("background")
        widget.configure(style="Success.TLabel" if color == ModernTheme.SUCCESS else "Danger.TLabel")
        self.after(800, lambda: widget.configure(style="Body.TLabel"))

    def _request_coach(self):
        self.feedback.config(text="📞 Request sent to coach - awaiting response...")

    def _refresh(self):
        self._poll()
        self.feedback.config(text="✓ Data refreshed")
