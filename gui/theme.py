"""
Apple-inspired modern theme for the GUI.
Following Apple's Human Interface Guidelines for clarity, deference, and aesthetic integrity.
"""
import tkinter as tk
from tkinter import ttk


class ModernTheme:
    """Apple-inspired dark theme with refined styling following HIG principles."""

    # Refined color palette (Apple-inspired)
    PRIMARY = "#007AFF"          # Apple blue - vibrant but not harsh
    PRIMARY_VARIANT = "#4DA3FF"  # Lighter blue for hover states
    SECONDARY = "#5AC8FA"        # Light blue for secondary actions
    SUCCESS = "#30D158"          # Apple green - slightly more vibrant
    WARNING = "#FF9F0A"          # Orange - warmer tone
    DANGER = "#FF453A"           # Red - Apple's destructive color
    BG_DARK = "#1C1C1E"          # Dark background - Apple's system gray 6
    BG_CARD = "#2C2C2E"          # Card background - Apple's system gray 5
    BG_SURFACE = "#3A3A3C"       # Surface background - Apple's system gray 4
    BG_GLASS = "#2F2F36"         # Glass card surface - subtle smoky transparency illusion
    BG_GLASS_LIGHT = "#383840"   # Lighter glass surface for nested panels
    TEXT_PRIMARY = "#FFFFFF"     # White text - maximum contrast
    TEXT_SECONDARY = "#EBEBF5"   # Light gray - Apple's system gray 2
    TEXT_TERTIARY = "#8E8E93"    # Medium gray - Apple's system gray
    BORDER = "#5B5B68"           # Border color - subtle separation in glass cards
    DIVIDER = "#38383A"          # Divider color - very subtle

    # Typography scale (following Apple's type scale)
    FONT_FAMILY = "SF Pro Display" if tk.Tk().call("tk", "windowingsystem") == "aqua" else "Helvetica"

    @staticmethod
    def configure(root):
        """Apply Apple-inspired theme to the application."""
        root.configure(bg=ModernTheme.BG_DARK)

        style = ttk.Style()
        style.theme_use("clam")

        # Configure label styles with proper hierarchy
        style.configure("TLabel",
                       background=ModernTheme.BG_DARK,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       font=(ModernTheme.FONT_FAMILY, 13))

        style.configure("Title.TLabel",
                       background=ModernTheme.BG_DARK,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       font=(ModernTheme.FONT_FAMILY, 28, "bold"),
                       padding=(0, 16, 0, 8))

        style.configure("Header.TLabel",
                       background=ModernTheme.BG_DARK,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       font=(ModernTheme.FONT_FAMILY, 20, "bold"),
                       padding=(0, 12, 0, 4))

        style.configure("Subheader.TLabel",
                       background=ModernTheme.BG_DARK,
                       foreground=ModernTheme.TEXT_SECONDARY,
                       font=(ModernTheme.FONT_FAMILY, 15, "bold"),
                       padding=(0, 8, 0, 2))

        style.configure("Body.TLabel",
                       background=ModernTheme.BG_DARK,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       font=(ModernTheme.FONT_FAMILY, 15),
                       padding=(0, 4))

        style.configure("Caption.TLabel",
                       background=ModernTheme.BG_DARK,
                       foreground=ModernTheme.TEXT_TERTIARY,
                       font=(ModernTheme.FONT_FAMILY, 12),
                       padding=(0, 2))

        style.configure("Tip.TLabel",
                       background=ModernTheme.BG_DARK,
                       foreground=ModernTheme.TEXT_SECONDARY,
                       font=(ModernTheme.FONT_FAMILY, 12, "italic"),
                       padding=(0, 2))

        style.configure("Glass.TLabel",
                       background=ModernTheme.BG_GLASS,
                       foreground=ModernTheme.TEXT_SECONDARY,
                       font=(ModernTheme.FONT_FAMILY, 14))

        style.configure("Status.TLabel",
                       background=ModernTheme.BG_DARK,
                       foreground=ModernTheme.TEXT_TERTIARY,
                       font=(ModernTheme.FONT_FAMILY, 11),
                       padding=(0, 2))

        # Configure button styles with proper feedback
        style.configure("TButton",
                       background=ModernTheme.PRIMARY,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       font=(ModernTheme.FONT_FAMILY, 13, "bold"),
                       padding=(16, 8),
                       borderwidth=0,
                       relief="flat",
                       anchor="center")

        style.map("TButton",
                 background=[("active", ModernTheme.PRIMARY_VARIANT),
                           ("pressed", ModernTheme.PRIMARY_VARIANT),
                           ("disabled", ModernTheme.TEXT_TERTIARY)],
                 foreground=[("disabled", ModernTheme.BG_SURFACE)])

        # Success button with refined styling
        style.configure("Success.TButton",
                       background=ModernTheme.SUCCESS,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       font=(ModernTheme.FONT_FAMILY, 13, "bold"),
                       padding=(16, 8),
                       borderwidth=0,
                       relief="flat")

        style.map("Success.TButton",
                 background=[("active", "#30DB5B"),
                           ("pressed", "#30DB5B"),
                           ("disabled", ModernTheme.TEXT_TERTIARY)],
                 foreground=[("disabled", ModernTheme.BG_SURFACE)])

        # Danger button with refined styling
        style.configure("Danger.TButton",
                       background=ModernTheme.DANGER,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       font=(ModernTheme.FONT_FAMILY, 13, "bold"),
                       padding=(16, 8),
                       borderwidth=0,
                       relief="flat")

        style.map("Danger.TButton",
                 background=[("active", "#FF6961"),
                           ("pressed", "#FF6961"),
                           ("disabled", ModernTheme.TEXT_TERTIARY)],
                 foreground=[("disabled", ModernTheme.BG_SURFACE)])

        # Secondary button for less prominent actions
        style.configure("Secondary.TButton",
                       background=ModernTheme.BG_SURFACE,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       font=(ModernTheme.FONT_FAMILY, 13),
                       padding=(16, 8),
                       borderwidth=0,
                       relief="flat")

        style.map("Secondary.TButton",
                 background=[("active", ModernTheme.BORDER),
                           ("pressed", ModernTheme.BORDER)])

        # Configure frame styles with proper layering
        style.configure("TFrame", background=ModernTheme.BG_DARK)
        style.configure("Card.TFrame",
                       background=ModernTheme.BG_GLASS,
                       relief="flat",
                       borderwidth=1)
        style.configure("Glass.TFrame",
                       background=ModernTheme.BG_GLASS,
                       relief="flat",
                       borderwidth=1)
        style.configure("GlassHighlight.TFrame",
                       background=ModernTheme.BG_GLASS_LIGHT,
                       relief="flat",
                       borderwidth=1)
        style.configure("Surface.TFrame",
                       background=ModernTheme.BG_SURFACE,
                       relief="flat",
                       borderwidth=0)
        style.configure("Toolbar.TFrame",
                       background=ModernTheme.BG_DARK,
                       relief="flat",
                       borderwidth=0,
                       padding=(16, 12))

        # Configure notebook styles with better visual hierarchy
        style.configure("TNotebook",
                       background=ModernTheme.BG_DARK,
                       borderwidth=0,
                       tabmargins=[0, 0, 0, 0])

        style.configure("TNotebook.Tab",
                       background=ModernTheme.BG_SURFACE,
                       foreground=ModernTheme.TEXT_SECONDARY,
                       padding=[24, 12],
                       font=(ModernTheme.FONT_FAMILY, 13),
                       borderwidth=0,
                       relief="flat")

        style.map("TNotebook.Tab",
                 background=[("selected", ModernTheme.BG_DARK),
                           ("active", ModernTheme.BG_CARD)],
                 foreground=[("selected", ModernTheme.TEXT_PRIMARY)])

        # Configure treeview styles with better readability
        style.configure("Treeview",
                       background=ModernTheme.BG_CARD,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       fieldbackground=ModernTheme.BG_CARD,
                       borderwidth=0,
                       font=(ModernTheme.FONT_FAMILY, 13),
                       rowheight=28)

        style.configure("Treeview.Heading",
                       background=ModernTheme.BG_SURFACE,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       font=(ModernTheme.FONT_FAMILY, 13, "bold"),
                       borderwidth=0,
                       padding=[8, 4])

        style.map("Treeview",
                 background=[("selected", ModernTheme.PRIMARY)],
                 foreground=[("selected", ModernTheme.TEXT_PRIMARY)])

        # Configure entry styles
        style.configure("TEntry",
                       background=ModernTheme.BG_SURFACE,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       fieldbackground=ModernTheme.BG_SURFACE,
                       borderwidth=0,
                       font=(ModernTheme.FONT_FAMILY, 15),
                       padding=[8, 6])

        style.map("TEntry",
                 background=[("focus", ModernTheme.BG_CARD)])

        return style
