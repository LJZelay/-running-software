"""
Modern high-tech theme for the GUI.
"""
import tkinter as tk
from tkinter import ttk


class ModernTheme:
    """Apple-inspired dark theme with modern styling."""

    # Color palette
    PRIMARY = "#007AFF"          # Apple blue
    SECONDARY = "#5AC8FA"        # Light blue
    SUCCESS = "#34C759"          # Green
    WARNING = "#FF9500"          # Orange
    DANGER = "#FF3B30"           # Red
    BG_DARK = "#1C1C1E"          # Dark background
    BG_CARD = "#2C2C2E"          # Card background
    TEXT_PRIMARY = "#FFFFFF"     # White text
    TEXT_SECONDARY = "#8E8E93"   # Gray text
    BORDER = "#3A3A3C"           # Border color

    @staticmethod
    def configure(root):
        """Apply modern theme to the application."""
        root.configure(bg=ModernTheme.BG_DARK)

        style = ttk.Style()
        style.theme_use("clam")

        # Configure label styles
        style.configure("TLabel", background=ModernTheme.BG_DARK, foreground=ModernTheme.TEXT_PRIMARY)
        style.configure("Title.TLabel", background=ModernTheme.BG_DARK, foreground=ModernTheme.TEXT_PRIMARY,
                       font=("Helvetica", 24, "bold"))
        style.configure("Header.TLabel", background=ModernTheme.BG_DARK, foreground=ModernTheme.TEXT_PRIMARY,
                       font=("Helvetica", 16, "bold"))
        style.configure("Subheader.TLabel", background=ModernTheme.BG_DARK, foreground=ModernTheme.SECONDARY,
                       font=("Helvetica", 11, "bold"))
        style.configure("Status.TLabel", background=ModernTheme.BG_DARK, foreground=ModernTheme.TEXT_SECONDARY,
                       font=("Helvetica", 9))

        # Configure button styles
        style.configure("TButton", background=ModernTheme.PRIMARY, foreground=ModernTheme.TEXT_PRIMARY,
                       font=("Helvetica", 10, "bold"), padding=8, borderwidth=0)
        style.map("TButton",
                 background=[("active", ModernTheme.SECONDARY), ("pressed", ModernTheme.PRIMARY)])

        style.configure("Success.TButton", background=ModernTheme.SUCCESS, foreground=ModernTheme.TEXT_PRIMARY,
                       font=("Helvetica", 10, "bold"), padding=8, borderwidth=0)
        style.map("Success.TButton",
                 background=[("active", "#52D273"), ("pressed", ModernTheme.SUCCESS)])

        style.configure("Danger.TButton", background=ModernTheme.DANGER, foreground=ModernTheme.TEXT_PRIMARY,
                       font=("Helvetica", 10, "bold"), padding=8, borderwidth=0)
        style.map("Danger.TButton",
                 background=[("active", "#FF453A"), ("pressed", ModernTheme.DANGER)])

        # Configure frame styles
        style.configure("TFrame", background=ModernTheme.BG_DARK)
        style.configure("Card.TFrame", background=ModernTheme.BG_CARD, relief="flat")
        style.configure("Toolbar.TFrame", background=ModernTheme.BG_DARK, relief="flat")

        # Configure notebook styles
        style.configure("TNotebook", background=ModernTheme.BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=ModernTheme.BG_CARD, foreground=ModernTheme.TEXT_PRIMARY,
                       padding=[20, 10], font=("Helvetica", 10))
        style.map("TNotebook.Tab", background=[("selected", ModernTheme.BG_DARK)])

        # Configure treeview styles
        style.configure("Treeview", background=ModernTheme.BG_CARD, foreground=ModernTheme.TEXT_PRIMARY,
                       fieldbackground=ModernTheme.BG_CARD, borderwidth=1)
        style.configure("Treeview.Heading", background=ModernTheme.PRIMARY, foreground=ModernTheme.TEXT_PRIMARY,
                       borderwidth=0)
        style.map("Treeview", background=[("selected", ModernTheme.PRIMARY)])

        # Configure entry styles
        style.configure("TEntry", background=ModernTheme.BG_CARD, foreground=ModernTheme.TEXT_PRIMARY,
                       fieldbackground=ModernTheme.BG_CARD, borderwidth=1)

        return style
