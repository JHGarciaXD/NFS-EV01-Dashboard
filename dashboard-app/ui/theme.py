"""
ui/theme.py
Color themes and the T() accessor used by all screens and widgets.
"""

LIGHT: dict = {
    "screen_bg": (255, 255, 255),
    "panel_bg":  (255, 255, 255),
    "fill_bg":   (230, 230, 230),
    "border":    (10,  10,  10),
    "text":      (0,   0,   0),
    "ok":        (0,   100, 0),
    "warn":      (200, 100, 0),
    "err":       (200, 0,   0),
    "button_bg": (235, 235, 235),
    "button_fg": (0,   0,   0),
}

DARK: dict = {
    "screen_bg": (15,  15,  18),
    "panel_bg":  (28,  28,  32),
    "fill_bg":   (38,  38,  44),
    "border":    (200, 200, 200),
    "text":      (240, 240, 240),
    "ok":        (80,  220, 120),
    "warn":      (255, 170, 40),
    "err":       (255, 80,  80),
    "button_bg": (55,  55,  65),
    "button_fg": (240, 240, 240),
}

# Mutable state — toggled by the UI
_dark_mode: bool = False


def is_dark() -> bool:
    return _dark_mode


def set_dark(value: bool) -> None:
    global _dark_mode
    _dark_mode = value


def toggle() -> bool:
    """Flip dark mode and return the new value."""
    global _dark_mode
    _dark_mode = not _dark_mode
    return _dark_mode


def T() -> dict:
    """Return the currently active theme dict."""
    return DARK if _dark_mode else LIGHT