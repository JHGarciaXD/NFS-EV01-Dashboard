import pygame
from service.tsal import TSALService

from ui import theme
from ui.widgets import (
    FONT_MED,
    draw_banner,
    draw_battery_bar,
    draw_button,
    draw_rect_value,
    draw_segment_bar,
    draw_temp_box,
    draw_tsal_indicator,  # ← ADD (add this function to widgets.py too)
)

W, H = 800, 480
_BTN_THEME = pygame.Rect(560, 240, 90, 45)
_BTN_MENU = pygame.Rect(560, 295, 90, 45)


class DashboardScreen:
    def __init__(self, tsal: TSALService):  # ← ADD
        self._tsal = tsal
        self._tsal.inject_lv()
        self._hv_on = False
        self._blink_on = False
        self._last_ms = 0

    def handle_event(self, event: pygame.event.Event) -> str | None:
        # ── TSAL keyboard inject ──────────────────────────────────────────
        if event.type == pygame.KEYDOWN:  # ← ADD block
            if event.key == pygame.K_l:
                self._tsal.inject_lv()
            elif event.key == pygame.K_h:
                self._tsal.inject_hv()
            elif event.key == pygame.K_F1:  # kill HV for testing
                self._tsal.inject_hv_off()

            # FOR TESTING K KEY SIMULATES TURN ON THE HV SYSTEM
            elif event.key == pygame.K_k:
                if self._tsal.state == "red_blink":
                    self._tsal.inject_hv_off()
                else:
                    self._tsal.inject_hv()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if _BTN_THEME.collidepoint(event.pos):
                new_dark = theme.toggle()
                print(f"[THEME] Dark mode -> {new_dark}")
            elif _BTN_MENU.collidepoint(event.pos):
                return "menu"
        return None

    def draw(self, surface: pygame.Surface, latest: dict) -> None:
        surface.fill(theme.T()["screen_bg"])
        draw_segment_bar(surface, 0, 0, 50, 405, latest["apps_pct"], mode="heat")
        draw_segment_bar(surface, 750, 0, 50, 405, latest["brake"], mode="cool")
        draw_rect_value(surface, 265, 115, 270, 230, latest["speed"], "Speed")
        draw_temp_box(
            surface, 140, 115, 105, 105, latest["battery_temp"], "Battery temp"
        )
        draw_temp_box(surface, 140, 240, 105, 105, latest["water_temp"], "Water temp")
        draw_temp_box(surface, 560, 115, 105, 105, latest["inv_temp"], "Inverter temp")
        draw_battery_bar(surface, 0, 405, 800, 75, latest["battery"])

        # Status banner
        t = theme.T()
        if latest["status_bits"] != 0:
            draw_banner(surface, "FAULT", t["err"], W // 2, 60)
        elif not latest["can_counter_ok"]:
            draw_banner(surface, "CAN DROP", t["warn"], W // 2, 60)
        else:
            draw_banner(surface, "OK", t["ok"], W // 2, 60)

        # TSAL indicator — top-right corner, above the buttons
        draw_tsal_indicator(surface, 58, 10, self._tsal.state, self._tsal.relay_on)
        label = "Dark" if not theme.is_dark() else "Light"
        draw_button(surface, _BTN_THEME, label)
        draw_button(surface, _BTN_MENU, "Menu")
