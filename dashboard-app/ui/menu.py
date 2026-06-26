"""
ui/menu.py
Menu screen — shows cards that navigate to sub-pages.

  handle_event(event) -> str | None
  draw(surface, latest)
"""

import pygame

from ui import theme
from ui.widgets import FONT_MED, FONT_SMALL

W, H = 800, 480

# ---------------------------------------------------------------------------
# Card definitions — add new pages here, they lay out automatically
# ---------------------------------------------------------------------------
_CARDS = [
    {
        "label": "Traction Control",
        "sublabel": "Adjust TC level (1–10)",
        "target": "tc",
        "icon": "TC",
    },
    {
        "label": "Startup Sequence",
        "sublabel": "Test TSAL interlock chain",
        "target": "startup",
        "icon": "TS",
    },
    # Future cards go here, e.g.:
    # {"label": "Brake Bias",  "sublabel": "Front/rear balance", "target": "brake_bias", "icon": "BB"},
    # {"label": "Diagnostics", "sublabel": "Live fault codes",   "target": "diag",       "icon": "DX"},
]

_CARD_W = 200
_CARD_H = 140
_CARD_GAP = 30
_CARD_Y = 160  # top edge of card row
_BTN_BACK = pygame.Rect(20, 20, 100, 45)


# Pre-compute card rects centered on screen
def _make_card_rects():
    n = len(_CARDS)
    total = n * _CARD_W + (n - 1) * _CARD_GAP
    x0 = (W - total) // 2
    return [
        pygame.Rect(x0 + i * (_CARD_W + _CARD_GAP), _CARD_Y, _CARD_W, _CARD_H)
        for i in range(n)
    ]


_CARD_RECTS = _make_card_rects()

# Fonts for cards
pygame.font.init()
_F_ICON = pygame.font.SysFont("DejaVu Sans", 36, bold=True)
_F_LABEL = pygame.font.SysFont("DejaVu Sans", 18, bold=True)
_F_SUB = pygame.font.SysFont("DejaVu Sans Mono", 12)
_F_TITLE = pygame.font.SysFont("DejaVu Sans", 42, bold=True)
_F_BACK = pygame.font.SysFont("DejaVu Sans", 20, bold=True)


def _draw_card(surface, rect, card, hovered):
    t = theme.T()
    bg = t["fill_bg"] if not hovered else t["button_bg"]
    pygame.draw.rect(surface, bg, rect, border_radius=18)
    pygame.draw.rect(surface, t["border"], rect, width=3, border_radius=18)

    # Icon badge
    badge = pygame.Rect(rect.x + 12, rect.y + 12, 52, 38)
    pygame.draw.rect(surface, t["button_bg"], badge, border_radius=8)
    icon = _F_ICON.render(card["icon"], True, t["ok"])
    surface.blit(icon, icon.get_rect(center=badge.center))

    # Label
    lbl = _F_LABEL.render(card["label"], True, t["text"])
    surface.blit(lbl, (rect.x + 14, rect.y + 62))

    # Sub-label (word-wrapped manually at ~26 chars)
    words = card["sublabel"]
    sub = _F_SUB.render(words, True, t["border"])
    surface.blit(sub, (rect.x + 14, rect.y + 90))

    # Arrow
    arrow = _F_LABEL.render("→", True, t["ok"])
    surface.blit(arrow, arrow.get_rect(bottomright=(rect.right - 14, rect.bottom - 12)))


class MenuScreen:
    def __init__(self):
        self._hovered = -1  # index of card under mouse, or -1

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.MOUSEMOTION:
            self._hovered = -1
            for i, r in enumerate(_CARD_RECTS):
                if r.collidepoint(event.pos):
                    self._hovered = i

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if _BTN_BACK.collidepoint(event.pos):
                return "dashboard"
            for i, r in enumerate(_CARD_RECTS):
                if r.collidepoint(event.pos):
                    return _CARDS[i]["target"]

        return None

    def draw(self, surface: pygame.Surface, latest: dict) -> None:
        t = theme.T()
        surface.fill(t["screen_bg"])

        # Title
        title = _F_TITLE.render("MENU", True, t["text"])
        surface.blit(title, title.get_rect(center=(W // 2, 85)))

        # Cards
        for i, (card, rect) in enumerate(zip(_CARDS, _CARD_RECTS)):
            _draw_card(surface, rect, card, hovered=(i == self._hovered))

        # Back button
        pygame.draw.rect(surface, t["button_bg"], _BTN_BACK, border_radius=10)
        pygame.draw.rect(surface, t["border"], _BTN_BACK, width=2, border_radius=10)
        lbl = _F_BACK.render("← Back", True, t["button_fg"])
        surface.blit(lbl, lbl.get_rect(center=_BTN_BACK.center))
