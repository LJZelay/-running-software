import threading
from typing import Callable
import tkinter as tk
from tkinter import messagebox

def show_error_dialog(title, message):
    """Show an error dialog."""
    messagebox.showerror(title, message)

def show_info_dialog(title, message):
    """Show an info dialog."""
    messagebox.showinfo(title, message)

class PollingTimer:
    """
    A simple periodic callback using tkinter's after method.
    (We'll just use root.after directly in the views.)
    """
    pass  # Not needed; we use after in the frames.