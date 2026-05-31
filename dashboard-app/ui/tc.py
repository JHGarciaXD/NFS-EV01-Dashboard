"""
ui/tc.py
Traction Control settings screen.

TC level: integer 1–10, sent on CAN ID 0x120
  [0] = TC level (1..10)
  [1] = 0x01 (magic byte so the MCU knows it's a TC command)
  [2..7] = reserved (0x00)

  handle_event(event) -> str | None
  draw(surface, latest)
"""

import pygame
import can
from ui import theme
from ui.widgets import FONT_MED, FONT_SMALL

W, H = 800, 480

ID_TC        = 0x120
TC_MIN       = 1
TC_MAX       = 10
TC_MAGIC     = 0x01   # byte[1] — lets the MCU distinguish TC frames

pygame.font.init()
_F_TITLE  = pygame.font.SysFont("DejaVu Sans", 42, bold=True)
_F_VALUE  = pygame.font.Font("assets/fonts/DSEG14Classic-Bold.ttf", 90)
_F_LABEL  = pygame.font.SysFont("DejaVu Sans", 20, bold=True)
_F_BTN    = pygame.font.SysFont("DejaVu Sans", 36, bold=True)
_F_BACK   = pygame.font.SysFont("DejaVu Sans", 20, bold=True)
_F_STATUS = pygame.font.SysFont("DejaVu Sans Mono", 14)

# Button rects
_BTN_MINUS = pygame.Rect(180, 200, 120, 120)
_BTN_PLUS  = pygame.Rect(500, 200, 120, 120)
_BTN_SEND  = pygame.Rect(W // 2 - 110, 360, 220, 55)
_BTN_BACK  = pygame.Rect(20, 20, 100, 45)


def _send_tc(bus: can.BusABC | None, level: int) -> str:
    """Send the TC level on CAN. Returns a status string."""
    if bus is None:
        return f"[NO BUS] TC={level} (not sent)"
    try:
        msg = can.Message(
            arbitration_id=ID_TC,
            data=[level, TC_MAGIC, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
            is_extended_id=False,
        )
        bus.send(msg)
        return f"Sent TC={level} on 0x{ID_TC:03X}  ✓"
    except can.CanError as e:
        return f"CAN error: {e}"


def _draw_round_btn(surface, rect, label, hovered):
    t  = theme.T()
    bg = t["fill_bg"] if not hovered else t["button_bg"]
    pygame.draw.ellipse(surface, bg,          rect)
    pygame.draw.ellipse(surface, t["border"], rect, width=3)
    txt = _F_BTN.render(label, True, t["text"])
    surface.blit(txt, txt.get_rect(center=rect.center))


class TCScreen:
    def __init__(self, bus: can.BusABC | None = None):
        self._bus      = bus
        self._level    = 5          # default TC level
        self._status   = ""         # last send status message
        self._hovered  = None       # "minus" | "plus" | "send" | None

    def set_bus(self, bus: can.BusABC) -> None:
        """Call this after the bus is open so TC can transmit."""
        self._bus = bus

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.MOUSEMOTION:
            p = event.pos
            if _BTN_MINUS.collidepoint(p):   self._hovered = "minus"
            elif _BTN_PLUS.collidepoint(p):  self._hovered = "plus"
            elif _BTN_SEND.collidepoint(p):  self._hovered = "send"
            else:                            self._hovered = None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if _BTN_BACK.collidepoint(event.pos):
                return "menu"

            if _BTN_MINUS.collidepoint(event.pos):
                self._level  = max(TC_MIN, self._level - 1)
                self._status = ""

            elif _BTN_PLUS.collidepoint(event.pos):
                self._level  = min(TC_MAX, self._level + 1)
                self._status = ""

            elif _BTN_SEND.collidepoint(event.pos):
                self._status = _send_tc(self._bus, self._level)
                print(f"[TC] {self._status}")

        return None

    def draw(self, surface: pygame.Surface, latest: dict) -> None:
        t = theme.T()
        surface.fill(t["screen_bg"])

        # Title
        title = _F_TITLE.render("Traction Control", True, t["text"])
        surface.blit(title, title.get_rect(center=(W // 2, 70)))

        # Sub-label
        sub = _F_LABEL.render("TC Level", True, t["border"])
        surface.blit(sub, sub.get_rect(center=(W // 2, 175)))

        # Value display box
        vbox = pygame.Rect(W // 2 - 80, 190, 160, 130)
        pygame.draw.rect(surface, t["panel_bg"], vbox, border_radius=16)
        pygame.draw.rect(surface, t["border"],   vbox, width=3, border_radius=16)
        val = _F_VALUE.render(str(self._level), True, t["text"])
        surface.blit(val, val.get_rect(center=vbox.center))

        # Range indicator dots
        dot_y   = vbox.bottom + 12
        dot_gap = 22
        total_w = TC_MAX * dot_gap
        dot_x0  = W // 2 - total_w // 2
        for i in range(1, TC_MAX + 1):
            cx  = dot_x0 + (i - 1) * dot_gap + dot_gap // 2
            col = t["ok"] if i <= self._level else t["fill_bg"]
            pygame.draw.circle(surface, col,          (cx, dot_y), 7)
            pygame.draw.circle(surface, t["border"],  (cx, dot_y), 7, width=2)

        # − / + buttons
        _draw_round_btn(surface, _BTN_MINUS, "−", self._hovered == "minus")
        _draw_round_btn(surface, _BTN_PLUS,  "+", self._hovered == "plus")

        # Send button
        send_bg = t["ok"] if self._hovered == "send" else t["button_bg"]
        pygame.draw.rect(surface, send_bg,     _BTN_SEND, border_radius=14)
        pygame.draw.rect(surface, t["border"], _BTN_SEND, width=2, border_radius=14)
        slbl = _F_LABEL.render("Send to CAN  →", True, t["button_fg"])
        surface.blit(slbl, slbl.get_rect(center=_BTN_SEND.center))

        # Status line
        if self._status:
            col  = t["ok"] if "✓" in self._status else t["err"]
            stxt = _F_STATUS.render(self._status, True, col)
            surface.blit(stxt, stxt.get_rect(center=(W // 2, _BTN_SEND.bottom + 18)))

        # Back button
        pygame.draw.rect(surface, t["button_bg"], _BTN_BACK, border_radius=10)
        pygame.draw.rect(surface, t["border"],    _BTN_BACK, width=2, border_radius=10)
        blbl = _F_BACK.render("← Back", True, t["button_fg"])
        surface.blit(blbl, blbl.get_rect(center=_BTN_BACK.center))