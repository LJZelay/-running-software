import tkinter as tk
from tkinter import ttk, messagebox
import pprint
from application.workout_repo import list_workouts, load_workout_summary

class WorkoutRepoPage(tk.Toplevel):
    """A simple page to list and load saved workouts."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Saved Workouts")
        self.geometry("650x550")
        self.resizable(True, True)
        self.parent = parent
        self._setup_ui()

    def _setup_ui(self):
        self.workouts = list_workouts()
        self.selected_id = None
        label = ttk.Label(self, text="Saved Workouts", font=("Arial", 16, "bold"))
        label.pack(pady=12)

        if not self.workouts:
            empty_label = ttk.Label(self, text="No workouts found", font=("Arial", 12))
            empty_label.pack(pady=24)
            return

        # --- Treeview (list of workouts) with scrollbar ---
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        self.tree = ttk.Treeview(
            tree_frame, columns=("name", "date"), show="headings",
            selectmode="browse", yscrollcommand=tree_scroll.set
        )
        tree_scroll.config(command=self.tree.yview)
        self.tree.heading("name", text="Name")
        self.tree.heading("date", text="Date")
        self.tree.column("name", width=280)
        self.tree.column("date", width=200)

        for w in self.workouts:
            name = w.get("name", "")
            if not name or name.strip() == "":
                name = "Unnamed"
            date = w.get("date", "")
            if not date or date.strip() == "":
                date = "Unknown date"
            self.tree.insert("", "end", iid=w["workout_id"], values=(name, date))

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Double-1>", self._on_select)

        # --- Details area (text widget) with scrollbar ---
        details_frame = ttk.Frame(self)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        self.details = tk.Text(details_frame, height=12, state="disabled",
                               wrap="word", font=("Arial", 10))
        details_scroll = ttk.Scrollbar(details_frame, orient=tk.VERTICAL,
                                       command=self.details.yview)
        self.details.configure(yscrollcommand=details_scroll.set)

        self.details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        details_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_select(self, event):
        item = self.tree.focus()
        if not item:
            return
        workout_id = item
        data = load_workout_summary(workout_id)
        self.details.config(state="normal")
        self.details.delete("1.0", tk.END)
        if not data:
            self.details.insert(tk.END, "No data found for this workout.")
        else:
            self.details.insert(tk.END, pprint.pformat(data, indent=2))
        self.details.config(state="disabled")
