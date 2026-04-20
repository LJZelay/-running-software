import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from gui.theme import ModernTheme


class TimestampEditorView(tk.Toplevel):
    """
    Coach/admin window for manually correcting timestamps that the
    hardware recorded incorrectly for a single runner.
    """

    def __init__(
        self,
        parent,
        edit_timestamp_uc,
        repo,
        workout_id: int,
        runner_session,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.edit_timestamp_uc = edit_timestamp_uc
        self.repo = repo
        self.workout_id = workout_id
        self.runner_session = runner_session
        self.runner_id = runner_session.runner.id

        self.title(f"Edit Timestamps - {runner_session.runner.name}")
        self.geometry("760x560")
        ModernTheme.configure(self)
        self._setup_ui()
        self._populate_tree()

    def _setup_ui(self):
        header_frame = ttk.Frame(self, style="GlassHighlight.TFrame")
        header_frame.pack(fill=tk.X, side=tk.TOP)
        ttk.Label(
            header_frame,
            text=f"Edit Timestamps - {self.runner_session.runner.name}",
            style="Title.TLabel",
        ).pack(side=tk.LEFT, padx=(16, 0), pady=(12, 6))

        ttk.Label(
            self,
            text=(
                "Use this tool to manually correct timestamps that the hardware "
                "recorded incorrectly. Enter new timestamps in ISO 8601 format "
                "(e.g., 2026-02-08T10:00:05)."
            ),
            style="Tip.TLabel",
            wraplength=720,
        ).pack(anchor=tk.W, padx=16, pady=(8, 8))

        container = ttk.Frame(self, style="Card.TFrame", padding=(16, 12))
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        columns = ("kind", "index", "field", "lap", "timestamp")
        self.tree = ttk.Treeview(
            container, columns=columns, show="headings", style="Treeview"
        )
        self.tree.heading("kind", text="Kind")
        self.tree.heading("index", text="Index")
        self.tree.heading("field", text="Field")
        self.tree.heading("lap", text="Lap")
        self.tree.heading("timestamp", text="Timestamp (ISO 8601)")
        self.tree.column("kind", width=90, minwidth=70)
        self.tree.column("index", width=70, minwidth=60)
        self.tree.column("field", width=80, minwidth=60)
        self.tree.column("lap", width=70, minwidth=50)
        self.tree.column("timestamp", width=400, minwidth=220)

        scrollbar = ttk.Scrollbar(
            container, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", lambda e: self._on_edit_selected())

        button_frame = ttk.Frame(self, style="GlassHighlight.TFrame")
        button_frame.pack(fill=tk.X, padx=16, pady=(0, 16))

        ttk.Button(
            button_frame,
            text="Edit Selected",
            command=self._on_edit_selected,
            style="Success.TButton",
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            button_frame,
            text="Refresh",
            command=self._populate_tree,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            button_frame,
            text="Close",
            command=self.destroy,
            style="Secondary.TButton",
        ).pack(side=tk.RIGHT)

    def _reload_runner_session(self):
        if not self.repo:
            return
        workout = self.repo.get_by_id(self.workout_id)
        if not workout:
            return
        rs = next(
            (s for s in workout.runnerSessions if s.runner.id == self.runner_id),
            None,
        )
        if rs:
            self.runner_session = rs

    def _populate_tree(self):
        self._reload_runner_session()
        self.tree.delete(*self.tree.get_children())

        for interval in self.runner_session.intervals:
            interval_number = interval.get("intervalNumber")
            self.tree.insert(
                "",
                tk.END,
                iid=f"interval|{interval_number}|start|",
                values=(
                    "interval",
                    interval_number,
                    "start",
                    "",
                    interval.get("start") or "",
                ),
            )
            for i, lap_ts in enumerate(interval.get("laps", [])):
                self.tree.insert(
                    "",
                    tk.END,
                    iid=f"interval|{interval_number}|lap|{i}",
                    values=(
                        "interval",
                        interval_number,
                        "lap",
                        i + 1,
                        lap_ts or "",
                    ),
                )
            self.tree.insert(
                "",
                tk.END,
                iid=f"interval|{interval_number}|end|",
                values=(
                    "interval",
                    interval_number,
                    "end",
                    "",
                    interval.get("end") or "",
                ),
            )

        for i, rest in enumerate(self.runner_session.rests):
            self.tree.insert(
                "",
                tk.END,
                iid=f"rest|{i}|start|",
                values=("rest", i, "start", "", rest.get("start") or ""),
            )
            self.tree.insert(
                "",
                tk.END,
                iid=f"rest|{i}|end|",
                values=("rest", i, "end", "", rest.get("end") or ""),
            )

    def _on_edit_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(
                "Edit Timestamp", "Select a row to edit.", parent=self
            )
            return

        iid = selection[0]
        try:
            kind, index_str, field, lap_str = iid.split("|")
            index = int(index_str)
            lap_index = int(lap_str) if lap_str != "" else None
        except ValueError:
            messagebox.showerror(
                "Edit Timestamp",
                "Could not parse the selected row.",
                parent=self,
            )
            return

        current_values = self.tree.item(iid, "values")
        current_timestamp = (
            current_values[4] if len(current_values) >= 5 else ""
        )

        label = f"{kind} {index} {field}"
        if lap_index is not None:
            label += f" (lap {lap_index + 1})"

        new_timestamp = simpledialog.askstring(
            "Edit Timestamp",
            f"Enter new ISO 8601 timestamp for {label}:",
            initialvalue=current_timestamp,
            parent=self,
        )
        if new_timestamp is None:
            return
        new_timestamp = new_timestamp.strip()
        if not new_timestamp:
            messagebox.showerror(
                "Edit Timestamp",
                "Timestamp cannot be empty.",
                parent=self,
            )
            return

        try:
            previous = self.edit_timestamp_uc.execute(
                workout_id=self.workout_id,
                runner_id=self.runner_id,
                kind=kind,
                index=index,
                field=field,
                new_timestamp=new_timestamp,
                lap_index=lap_index,
            )
        except Exception as e:
            messagebox.showerror(
                "Edit Timestamp", f"Failed to edit: {e}", parent=self
            )
            return

        messagebox.showinfo(
            "Timestamp Updated",
            f"Changed {label}\nfrom: {previous}\n  to: {new_timestamp}",
            parent=self,
        )
        self._populate_tree()
