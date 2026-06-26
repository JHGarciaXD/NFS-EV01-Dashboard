"""
ui/temp_control.py
Temperature threshold control screen — Motor & Inverter only.

Each card has:
  - NTC sensor reading
  - Hot spot (CAN) reading
  - Fan state pill (auto or forced)
  - Threshold +/- buttons
  - FORCE button to override fan on regardless of temp
"""

import pygame

from ui import theme

W, H = 800, 480

# ── Layout ────────────────────────────────────────────────────
_CARD_W = 340
_CARD_H = 310  # taller to fit force button
_CARD_GAP = 40
_CARD_Y = 100
_BTN_H = 44
_BTN_W = 70
_FORCE_H = 38
_FORCE_W = 140

_BTN_BACK = pygame.Rect(20, 20, 100, 45)

_CH_LABELS = ["Motor", "Inverter"]
_CH_ICONS = ["MOT", "INV"]

pygame.font.init()
_F_TITLE = pygame.font.SysFont("DejaVu Sans", 38, bold=True)
_F_BACK = pygame.font.SysFont("DejaVu Sans", 20, bold=True)
_F_ICON = pygame.font.SysFont("DejaVu Sans", 15, bold=True)
_F_NAME = pygame.font.SysFont("DejaVu Sans", 22, bold=True)
_F_TEMP = pygame.font.SysFont("DejaVu Sans Mono", 36, bold=True)
_F_LABEL = pygame.font.SysFont("DejaVu Sans Mono", 12)
_F_THRESH = pygame.font.SysFont("DejaVu Sans Mono", 24, bold=True)
_F_BTN = pygame.font.SysFont("DejaVu Sans", 26, bold=True)
_F_FAN = pygame.font.SysFont("DejaVu Sans", 14, bold=True)
_F_FORCE = pygame.font.SysFont("DejaVu Sans", 14, bold=True)
_F_HINT = pygame.font.SysFont("DejaVu Sans Mono", 11)


def _card_rects():
    n = len(_CH_LABELS)
    total = n * _CARD_W + (n - 1) * _CARD_GAP
    x0 = (W - total) // 2
    return [
        pygame.Rect(x0 + i * (_CARD_W + _CARD_GAP), _CARD_Y, _CARD_W, _CARD_H)
        for i in range(n)
    ]


_CARD_RECTS = _card_rects()


class TempControlScreen:
    def __init__(self, bus, service):
        self._bus = bus
        self._svc = service
        self._hov = -1

        self._btn_minus: list[pygame.Rect] = []
        self._btn_plus: list[pygame.Rect] = []
        self._btn_force: list[pygame.Rect] = []

        for rect in _CARD_RECTS:
            cx = rect.centerx

            # +/- threshold buttons — second row from bottom
            thresh_btn_y = rect.bottom - _BTN_H - _FORCE_H - 28
            self._btn_minus.append(
                pygame.Rect(cx - _BTN_W - 10, thresh_btn_y, _BTN_W, _BTN_H)
            )
            self._btn_plus.append(pygame.Rect(cx + 10, thresh_btn_y, _BTN_W, _BTN_H))

            # Force button — bottom of card
            force_y = rect.bottom - _FORCE_H - 12
            self._btn_force.append(
                pygame.Rect(cx - _FORCE_W // 2, force_y, _FORCE_W, _FORCE_H)
            )

    # ── Events ────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.MOUSEMOTION:
            self._hov = -1
            for i, r in enumerate(_CARD_RECTS):
                if r.collidepoint(event.pos):
                    self._hov = i

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if _BTN_BACK.collidepoint(event.pos):
                return "menu"
            for i in range(len(_CH_LABELS)):
                if self._btn_minus[i].collidepoint(event.pos):
                    self._svc.adjust_threshold(i, -5)
                elif self._btn_plus[i].collidepoint(event.pos):
                    self._svc.adjust_threshold(i, +5)
                elif self._btn_force[i].collidepoint(event.pos):
                    self._svc.toggle_force(i)

        return None

    # ── Draw ─────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, latest: dict) -> None:
        t = theme.T()
        surface.fill(t["screen_bg"])

        title = _F_TITLE.render("TEMPERATURES", True, t["text"])
        surface.blit(title, title.get_rect(center=(W // 2, 52)))

        for i in range(len(_CH_LABELS)):
            self._draw_card(surface, i, t)

        pygame.draw.rect(surface, t["button_bg"], _BTN_BACK, border_radius=10)
        pygame.draw.rect(surface, t["border"], _BTN_BACK, width=2, border_radius=10)
        lbl = _F_BACK.render("← Back", True, t["button_fg"])
        surface.blit(lbl, lbl.get_rect(center=_BTN_BACK.center))

        hint = _F_HINT.render(
            "± 5 °C per tap  •  thresholds sent live via CAN 0x130  •  FORCE overrides temp logic",
            True,
            t["border"],
        )
        surface.blit(hint, hint.get_rect(center=(W // 2, H - 14)))

    def _draw_card(self, surface: pygame.Surface, i: int, t: dict) -> None:
        rect = _CARD_RECTS[i]
        svc = self._svc
        ntc = svc.analog_temp[i]
        hot = svc.can_temp[i]
        thresh = svc.thresholds[i]
        fan_on = svc.fan_state[i]
        forced = svc.fan_forced[i]
        fault = bool(svc.fault_mask & (1 << i))

        temps_valid = [v for v in (ntc, hot) if v > -90]
        worst = max(temps_valid) if temps_valid else -99.0
        near = worst >= thresh - 10
        over = worst >= thresh

        # Card background — forced gets a distinct amber tint
        if forced:
            bg = (60, 45, 10)
        elif over:
            bg = (80, 20, 20)
        elif near:
            bg = (65, 45, 10)
        else:
            bg = t["fill_bg"] if i != self._hov else t["button_bg"]

        pygame.draw.rect(surface, bg, rect, border_radius=18)
        # Forced gets an amber border to make it obvious
        border_col = (200, 140, 20) if forced else t["border"]
        pygame.draw.rect(surface, border_col, rect, width=2, border_radius=18)

        x, y = rect.x, rect.y

        # Icon + name
        badge = pygame.Rect(x + 14, y + 14, 52, 30)
        pygame.draw.rect(surface, t["button_bg"], badge, border_radius=7)
        ic = _F_ICON.render(_CH_ICONS[i], True, t["ok"])
        surface.blit(ic, ic.get_rect(center=badge.center))
        nm = _F_NAME.render(_CH_LABELS[i], True, t["text"])
        surface.blit(nm, (x + 76, y + 18))

        # Fan state pill — shows FORCED when applicable
        if forced:
            pill_col = (190, 130, 10)
            pill_text = "FAN FORCED ON"
        elif fan_on:
            pill_col = (170, 50, 50)
            pill_text = "FAN ON"
        else:
            pill_col = (35, 85, 35)
            pill_text = "fan off"
        pill = pygame.Rect(x + 14, y + 54, _CARD_W - 28, 26)
        pygame.draw.rect(surface, pill_col, pill, border_radius=7)
        ftxt = _F_FAN.render(pill_text, True, (230, 230, 230))
        surface.blit(ftxt, ftxt.get_rect(center=pill.center))

        # NTC row
        surface.blit(_F_LABEL.render("NTC sensor", True, t["border"]), (x + 14, y + 92))
        if fault or ntc < -90:
            a_str, a_col = "ERR", (220, 80, 80)
        else:
            a_str, a_col = f"{ntc:+.1f} °C", _temp_col(ntc, thresh, t)
        surface.blit(_F_TEMP.render(a_str, True, a_col), (x + 14, y + 106))

        # Hot spot row
        surface.blit(
            _F_LABEL.render("hot spot (CAN)", True, t["border"]), (x + 14, y + 154)
        )
        if hot < -90:
            h_str, h_col = "---", t["border"]
        else:
            h_str, h_col = f"{hot:+.1f} °C", _temp_col(hot, thresh, t)
        surface.blit(_F_TEMP.render(h_str, True, h_col), (x + 14, y + 168))

        # Threshold label + value
        thr_y = rect.bottom - _BTN_H - _FORCE_H - 48
        surface.blit(
            _F_LABEL.render("FAN THRESHOLD", True, t["border"]), (x + 14, thr_y)
        )
        thr_s = _F_THRESH.render(f"{thresh:.0f} °C", True, t["text"])
        surface.blit(thr_s, thr_s.get_rect(center=(rect.centerx, thr_y + 22)))

        # +/- buttons
        for btn, lbl in ((self._btn_minus[i], "−"), (self._btn_plus[i], "+")):
            pygame.draw.rect(surface, t["button_bg"], btn, border_radius=9)
            pygame.draw.rect(surface, t["border"], btn, width=2, border_radius=9)
            ls = _F_BTN.render(lbl, True, t["button_fg"])
            surface.blit(ls, ls.get_rect(center=btn.center))

        # Force button — amber when active, muted when off
        fbtn = self._btn_force[i]
        if forced:
            f_bg = (180, 120, 10)
            f_border = (220, 160, 30)
            f_text = "⬛ FORCED ON"
            f_col = (255, 240, 200)
        else:
            f_bg = t["button_bg"]
            f_border = t["border"]
            f_text = "FORCE ON"
            f_col = t["button_fg"]

        pygame.draw.rect(surface, f_bg, fbtn, border_radius=9)
        pygame.draw.rect(surface, f_border, fbtn, width=2, border_radius=9)
        fs = _F_FORCE.render(f_text, True, f_col)
        surface.blit(fs, fs.get_rect(center=fbtn.center))


def _temp_col(temp: float, thresh: float, t: dict):
    if temp >= thresh:
        return (255, 80, 80)
    if temp >= thresh - 10:
        return (255, 180, 50)
    return t["ok"]
