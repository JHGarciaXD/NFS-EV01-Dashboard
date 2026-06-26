"""
ui/startup.py
─────────────────────────────────────────────────────────────────────────────
Startup sequence screen — drawing only.
Logic lives in service/startup.py (StartupService).

Keyboard shortcuts:
  K  → inject key ON
  T  → inject TSMS closed
  Q  → abort, return to menu
"""

import pygame
from service.startup import (
    PHASE_KEY_WAIT,
    PHASE_LV_ON,
    PHASE_READY,
    PHASE_TSAL,
    PHASE_TSMS_WAIT,
    TSAL_BLINKS_REQUIRED,
    StartupService,
)

# ── Layout ────────────────────────────────────────────────────────────────
W, H = 800, 480
_CX = W // 2
_ROW_TOP = 100
_ROW_GAP = 90
_LED_R = 18
_LED_X = 140
_LABEL_X = 175

# ── Colours ───────────────────────────────────────────────────────────────
_WHITE = (255, 255, 255)
_GREEN = (50, 220, 80)
_RED = (220, 40, 40)
_GREY = (80, 80, 80)
_DIMGRY = (40, 40, 40)
_AMBER = (255, 180, 0)
_PANEL = (18, 18, 24)
_BORDER = (60, 60, 80)

_ABORT_BTN = pygame.Rect(W - 130, H - 50, 110, 36)

# ── Row definitions ───────────────────────────────────────────────────────
_ROWS = [
    # (phase_when_active, led_colour, label, status_text)
    (PHASE_KEY_WAIT, _GREEN, "LOW VOLTAGE", "ON"),
    (PHASE_TSMS_WAIT, _GREEN, "CAR KEY", "INSERTED"),
    (PHASE_TSAL, _AMBER, "TSMS / HV", "CLOSED — HV ACTIVE"),
    (PHASE_READY, _RED, "TSAL", "BLINKING"),
]


class StartupScreen:
    """
    Screen wrapper around StartupService.
    Follows the project's handle_event / draw protocol.
    """

    def __init__(self):
        self._svc = StartupService()
        self._fonts_ready = False
        self._aborted = False

    # ── Font lazy init ────────────────────────────────────────────────────
    def _ensure_fonts(self):
        if self._fonts_ready:
            return
        self._f_title = pygame.font.SysFont("monospace", 32, bold=True)
        self._f_label = pygame.font.SysFont("monospace", 22)
        self._f_status = pygame.font.SysFont("monospace", 20, bold=True)
        self._f_hint = pygame.font.SysFont("monospace", 15)
        self._f_ready = pygame.font.SysFont("monospace", 48, bold=True)
        self._fonts_ready = True

    # ── handle_event ──────────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_k:
                self._svc.inject_key()
                print("[UI/STARTUP] Key inject")
            elif event.key == pygame.K_t:
                self._svc.inject_tsms()
                print("[UI/STARTUP] TSMS inject")
            elif event.key == pygame.K_q:
                self._aborted = True

        if event.type == pygame.MOUSEBUTTONDOWN:
            if _ABORT_BTN.collidepoint(event.pos):
                self._aborted = True

        if self._aborted:
            self._aborted = False
            self._svc.reset()
            print("[UI/STARTUP] Aborted → menu")
            return "menu"

        return None

    # ── draw ──────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, can_data: dict) -> None:
        self._ensure_fonts()
        self._svc.tick(pygame.time.get_ticks())

        surface.fill(_PANEL)
        self._draw_title(surface)
        self._draw_rows(surface)
        self._draw_hints(surface)
        self._draw_abort_btn(surface)

        if self._svc.phase == PHASE_READY:
            self._draw_ready(surface)

    # ── wants_dashboard (checked by main loop) ────────────────────────────
    @property
    def wants_dashboard(self) -> bool:
        return self._svc.wants_dashboard

    # ── Draw helpers ──────────────────────────────────────────────────────
    def _draw_title(self, surface):
        txt = self._f_title.render("STARTUP SEQUENCE", True, _WHITE)
        surface.blit(txt, txt.get_rect(centerx=_CX, top=28))
        pygame.draw.line(surface, _BORDER, (60, 72), (W - 60, 72), 1)

    def _draw_rows(self, surface):
        phase = self._svc.phase
        blinks = self._svc.tsal_blinks

        for i, (phase_active, colour, label, status) in enumerate(_ROWS):
            y = _ROW_TOP + i * _ROW_GAP

            if phase > phase_active:
                led_col = _GREEN
                status_txt = "✓ DONE"
                status_col = _GREEN
            elif phase == phase_active:
                if label == "TSAL":
                    led_col = _RED if self._svc.tsal_on else _DIMGRY
                    status_txt = f"BLINKING  ({blinks} / {TSAL_BLINKS_REQUIRED})"
                    status_col = _RED
                else:
                    led_col = colour
                    status_txt = status
                    status_col = _AMBER
            else:
                led_col = _GREY
                status_txt = "WAITING…"
                status_col = _GREY

            pygame.draw.circle(surface, led_col, (_LED_X, y + 12), _LED_R)
            pygame.draw.circle(surface, _WHITE, (_LED_X, y + 12), _LED_R, 2)

            surface.blit(self._f_label.render(label, True, _WHITE), (_LABEL_X, y))
            surface.blit(
                self._f_status.render(status_txt, True, status_col), (_LABEL_X, y + 26)
            )

            if i < len(_ROWS) - 1:
                pygame.draw.line(
                    surface,
                    _BORDER,
                    (110, y + _ROW_GAP - 8),
                    (W - 110, y + _ROW_GAP - 8),
                    1,
                )

    def _draw_hints(self, surface):
        phase = self._svc.phase
        hints = {
            PHASE_KEY_WAIT: [
                "Press  K  to insert car key",
                "(or turn physical key switch ON)",
            ],
            PHASE_TSMS_WAIT: [
                "Press  T  to close TSMS",
                "(or flip Tractive System Master Switch)",
            ],
            PHASE_TSAL: [
                "Tractive system active — stand clear",
                "TSAL must blink at ≥ 2 Hz  (FSAE EV.8)",
            ],
        }.get(phase, [])

        for j, h in enumerate(hints):
            col = _AMBER if j == 0 else _GREY
            t = self._f_hint.render(h, True, col)
            surface.blit(t, t.get_rect(centerx=_CX, top=H - 78 + j * 20))

    def _draw_abort_btn(self, surface):
        pygame.draw.rect(surface, _DIMGRY, _ABORT_BTN, border_radius=8)
        pygame.draw.rect(surface, _BORDER, _ABORT_BTN, width=1, border_radius=8)
        lbl = self._f_hint.render("Q — Abort", True, _GREY)
        surface.blit(lbl, lbl.get_rect(center=_ABORT_BTN.center))

    def _draw_ready(self, surface):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 40, 0, 200))
        surface.blit(overlay, (0, 0))
        txt = self._f_ready.render("READY TO DRIVE", True, _GREEN)
        surface.blit(txt, txt.get_rect(center=(_CX, H // 2 - 20)))
        sub = self._f_label.render("Navigating to dashboard…", True, _WHITE)
        surface.blit(sub, sub.get_rect(center=(_CX, H // 2 + 40)))
