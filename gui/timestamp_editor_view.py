import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime

from gui.theme import ModernTheme


def _fmt_ts(ts_raw: str) -> str:
    """Return a human-friendly timestamp string, or '—' if empty/unparseable."""
    if not ts_raw:
        return "—"
    try:
        dt = datetime.fromisoformat(ts_raw)
        return dt.strftime("%b %d, %Y  %I:%M:%S %p")
    except Exception:
        return ts_raw


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
        undo_last_edit_uc=None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.edit_timestamp_uc = edit_timestamp_uc
        self.undo_last_edit_uc = undo_last_edit_uc
        self.repo = repo
        self.workout_id = workout_id
        self.runner_session = runner_session
        self.runner_id = runner_session.runner.id

        self._raw_timestamps: dict[str, str] = {}

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
                "Actions are listed in chronological order. "
                "Double-click any row (or select it and press Edit Selected) to correct its timestamp. "
                "Enter the new time in ISO 8601 format, e.g. 2026-02-08T10:00:05."
            ),
            style="Tip.TLabel",
            wraplength=720,
        ).pack(anchor=tk.W, padx=16, pady=(8, 8))

        container = ttk.Frame(self, style="Card.TFrame", padding=(16, 12))
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        columns = ("description", "timestamp")
        self.tree = ttk.Treeview(
            container, columns=columns, show="headings", style="Treeview"
        )
        self.tree.heading("description", text="Action")
        self.tree.heading("timestamp", text="Time")
        self.tree.column("description", width=280, minwidth=180)
        self.tree.column("timestamp", width=380, minwidth=200)

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
            text="Undo Last Edit",
            command=self._on_undo_last_edit,
            style="Secondary.TButton",
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
        self._raw_timestamps = {}

        # Collect every event as (raw_ts, iid, description)
        events: list[tuple[str, str, str]] = []

        for interval in self.runner_session.intervals:
            n = interval.get("intervalNumber")
            events.append((
                interval.get("start") or "",
                f"interval|{n}|start|",
                f"Interval {n} — Start",
            ))
            for i, lap_ts in enumerate(interval.get("laps", [])):
                events.append((
                    lap_ts or "",
                    f"interval|{n}|lap|{i}",
                    f"Interval {n} — Lap {i + 1}",
                ))
            events.append((
                interval.get("end") or "",
                f"interval|{n}|end|",
                f"Interval {n} — End",
            ))

        for i, rest in enumerate(self.runner_session.rests):
            events.append((
                rest.get("start") or "",
                f"rest|{i}|start|",
                f"Rest {i + 1} — Start",
            ))
            events.append((
                rest.get("end") or "",
                f"rest|{i}|end|",
                f"Rest {i + 1} — End",
            ))

        # Sort chronologically; rows with no timestamp fall to the bottom
        events.sort(key=lambda e: e[0] if e[0] else "9999")

        for ts_raw, iid, description in events:
            self._raw_timestamps[iid] = ts_raw
            self.tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(description, _fmt_ts(ts_raw)),
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

        current_timestamp = self._raw_timestamps.get(iid, "")

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

    def _on_undo_last_edit(self):
        if self.undo_last_edit_uc is None:
            messagebox.showerror(
                "Undo",
                "Undo is not configured.",
                parent=self,
            )
            return

        try:
            result = self.undo_last_edit_uc.execute(
                workout_id=self.workout_id,
                runner_id=self.runner_id,
            )
        except Exception as e:
            messagebox.showerror(
                "Undo", f"Failed to undo: {e}", parent=self
            )
            return

        if result is None:
            messagebox.showinfo(
                "Undo",
                "Nothing to undo for this runner.",
                parent=self,
            )
            return

        kind = result["kind"]
        index = result["index"]
        field = result["field"]
        reverted_from = result["reverted_from"]
        reverted_to = result["reverted_to"]
        label = f"{kind} {index} {field}"
        lap_index = result.get("lap_index")
        if lap_index is not None:
            label += f" (lap {lap_index + 1})"

        messagebox.showinfo(
            "Undo Successful",
            (
                f"Reverted {label}\n"
                f"from: {reverted_from}\n"
                f"  to: {reverted_to}"
            ),
            parent=self,
        )
        self._populate_tree()
