"""
ui/widgets.py
Reusable drawing primitives shared across screens.
Every function receives the pygame surface as its first argument.
"""

import pygame

from ui.theme import T

# ---------------------------------------------------------------------------
# Fonts — loaded once at import time
# ---------------------------------------------------------------------------
pygame.font.init()

FONT_BIG = pygame.font.SysFont("DejaVu Sans", 120, bold=True)
FONT_MED = pygame.font.SysFont("DejaVu Sans", 28, bold=True)
FONT_MID = pygame.font.SysFont("DejaVu Sans Mono", 16)
FONT_SMALL = pygame.font.SysFont("DejaVu Sans Mono", 12)

FONT_DIGITAL = pygame.font.Font("assets/fonts/DSEG14Classic-Bold.ttf", 100)
FONT_DIGITAL_MED = pygame.font.Font("assets/fonts/DSEG14Classic-Bold.ttf", 70)
FONT_DIGITAL_SMALLER = pygame.font.Font("assets/fonts/DSEG14Classic-Bold.ttf", 30)


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------


def heat_color_inverted(pct: float) -> tuple[int, int, int]:
    p = max(0, min(100, pct)) / 100.0
    bp = 0.3
    if p < bp:
        t = p / bp
        r = 255
        g = int(225 + 30 * (1 - t))
        b = int(255 * (1 - t))
    else:
        t = (p - bp) / (1 - bp)
        r = int(255 - 55 * t)
        g = int(255 * (1 - t))
        b = 0
    return (r, g, b)


def cool_color(pct: float) -> tuple[int, int, int]:
    p = max(0, min(100, pct)) / 100.0
    r = int(255 * (1 - p))
    g = int(255 * (1 - p * 0.7))
    b = int(255 - 55 * p)
    return (r, g, b)


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------


def draw_battery_bar(
    surface: pygame.Surface, x: int, y: int, w: int, h: int, pct: float
) -> None:
    pygame.draw.rect(surface, T()["fill_bg"], (x, y, w, h))
    if pct > 70:
        fill_color = (0, 100, 0)
    elif pct > 50:
        fill_color = (0, 200, 0)
    elif pct > 35:
        fill_color = (255, 200, 0)
    elif pct > 20:
        fill_color = (255, 100, 0)
    else:
        fill_color = (200, 0, 0)
    fill_w = int(w * max(0, min(100, pct)) / 100.0)
    pygame.draw.rect(surface, fill_color, (x, y, fill_w, h))
    pygame.draw.rect(surface, T()["border"], (x, y, w, h), 3)


def draw_rect_value(
    surface: pygame.Surface,
    x: int,
    y: int,
    w: int,
    h: int,
    value: float,
    label: str | None = None,
) -> None:
    pygame.draw.rect(surface, T()["panel_bg"], (x, y, w, h), border_radius=20)
    pygame.draw.rect(surface, T()["border"], (x, y, w, h), width=3, border_radius=20)
    txt = FONT_DIGITAL.render(f"{value:.0f}", True, T()["text"])
    surface.blit(txt, txt.get_rect(center=(x + int(w * 0.47), y + h // 2)))
    if label:
        lbl = FONT_SMALL.render(label, True, T()["text"])
        surface.blit(lbl, lbl.get_rect(center=(x + w // 2, y + 16)))


def draw_temp_box(
    surface: pygame.Surface, x: int, y: int, w: int, h: int, temp: float, label: str
) -> None:
    pygame.draw.rect(surface, T()["panel_bg"], (x, y, w, h), border_radius=20)
    pygame.draw.rect(surface, T()["border"], (x, y, w, h), width=3, border_radius=20)
    txt = FONT_DIGITAL_SMALLER.render(f"{temp:.0f}º", True, T()["text"])
    surface.blit(txt, txt.get_rect(center=(x + int(w * 0.47), y + h // 2)))
    lbl = FONT_SMALL.render(label, True, T()["text"])
    surface.blit(lbl, lbl.get_rect(center=(x + w // 2, y + 15)))


def draw_segment_bar(
    surface: pygame.Surface,
    x: int,
    y: int,
    w: int,
    h: int,
    pct: float,
    mode: str = "heat",
    segments: int = 40,
    gap: int = 1,
    border_radius: int = 0,
) -> None:
    pygame.draw.rect(surface, T()["fill_bg"], (x, y, w, h), border_radius=border_radius)
    pygame.draw.rect(
        surface, T()["border"], (x, y, w, h), width=3, border_radius=border_radius
    )
    p = max(0, min(100, pct)) / 100.0
    total_gap = gap * (segments - 1)
    seg_h = max(1, (h - total_gap) // segments)
    lit_full = int(p * segments)
    for i in range(segments):
        seg_bottom = y + h - (i + 1) * seg_h - i * gap + gap
        rect = pygame.Rect(x, seg_bottom, w, seg_h)
        rel = (i + 0.5) / segments
        col = (
            heat_color_inverted(rel * 100.0)
            if mode == "heat"
            else cool_color(rel * 100.0)
        )
        if i < lit_full:
            pygame.draw.rect(surface, col, rect, border_radius=border_radius // 2)
        else:
            pygame.draw.rect(
                surface, (210, 210, 210), rect, border_radius=border_radius // 2
            )
        pygame.draw.rect(
            surface, T()["border"], rect, width=1, border_radius=border_radius // 2
        )


def draw_banner(
    surface: pygame.Surface, text: str, color: tuple, cx: int, cy: int
) -> None:
    surf = FONT_DIGITAL_MED.render(text, True, color)
    rect = surf.get_rect(center=(cx, cy))
    surface.blit(surf, rect)


def draw_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font | None = None,
) -> None:
    """Generic bordered button; uses theme colors."""
    f = font or FONT_MED
    pygame.draw.rect(surface, T()["button_bg"], rect, border_radius=10)
    pygame.draw.rect(surface, T()["border"], rect, width=2, border_radius=10)
    txt = f.render(label, True, T()["button_fg"])
    surface.blit(txt, txt.get_rect(center=rect.center))


def draw_tsal_indicator(
    surface: pygame.Surface, x: int, y: int, state: str, relay_on: bool
):
    W_PIL, H_PIL = 34, 34  # square — just the LED circle
    rect = pygame.Rect(x, y, W_PIL, H_PIL)

    if state == "green":
        colour = (0, 255, 0)
    elif state == "red_blink":
        colour = (255, 0, 0) if relay_on else (255, 0, 0)
    else:  # "off"
        colour = (0, 255, 0)

    pygame.draw.circle(surface, colour, rect.center, W_PIL // 2)
    pygame.draw.circle(surface, (255, 255, 255), rect.center, W_PIL // 2, 2)
