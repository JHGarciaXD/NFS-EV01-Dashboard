"""
ui/dashboard.py
The main racing dashboard screen.

  handle_event(event) -> str | None   — returns next screen name or None
  draw(surface, latest)               — renders everything
"""

import pygame
from ui import theme
from ui.widgets import (
    draw_battery_bar,
    draw_rect_value,
    draw_temp_box,
    draw_segment_bar,
    draw_banner,
    draw_button,
    FONT_MED,
)

W, H = 800, 480

# Button rectangles — below the inverter temp box (x=560, clear of battery bar and segment bars)
_BTN_THEME = pygame.Rect(560, 240, 90, 45)
_BTN_MENU  = pygame.Rect(560, 295, 90, 45)


class DashboardScreen:
    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if _BTN_THEME.collidepoint(event.pos):
                new_dark = theme.toggle()
                print(f"[THEME] Dark mode → {new_dark}")

            elif _BTN_MENU.collidepoint(event.pos):
                return "menu"

        return None

    def draw(self, surface: pygame.Surface, latest: dict) -> None:
        surface.fill(theme.T()["screen_bg"])

        # Segment bars (left = APPS, right = Brake) — drawn first, behind everything
        draw_segment_bar(surface, 0,   0, 50, 405, latest["apps_pct"], mode="heat")
        draw_segment_bar(surface, 750, 0, 50, 405, latest["brake"],    mode="cool")

        # Speed (centre)
        draw_rect_value(surface, 265, 115, 270, 230, latest["speed"], "Speed")

        # Temperature boxes
        draw_temp_box(surface, 140, 115, 105, 105, latest["battery_temp"], "Battery temp")
        draw_temp_box(surface, 140, 240, 105, 105, latest["water_temp"],   "Water temp")
        draw_temp_box(surface, 560, 115, 105, 105, latest["inv_temp"],     "Inverter temp")

        # Battery bar (bottom strip)
        draw_battery_bar(surface, 0, 405, 800, 75, latest["battery"])

        # Status banner
        t = theme.T()
        if latest["status_bits"] != 0:
            draw_banner(surface, "FAULT",    t["err"],  W // 2, 60)
        elif not latest["can_counter_ok"]:
            draw_banner(surface, "CAN DROP", t["warn"], W // 2, 60)
        else:
            draw_banner(surface, "OK",       t["ok"],   W // 2, 60)

        # Buttons — drawn last so nothing paints over them
        label = "Dark" if not theme.is_dark() else "Light"
        draw_button(surface, _BTN_THEME, label)
        draw_button(surface, _BTN_MENU,  "Menu")