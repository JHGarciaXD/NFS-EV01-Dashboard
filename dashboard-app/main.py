"""
main.py
Entry point for the FS Dashboard.
Run with:
    python main.py
"""

import can
import can_rx
import pygame
from ui.dashboard import DashboardScreen
from ui.menu import MenuScreen
from ui.startup import StartupScreen  # was service.startup
from ui.tc import TCScreen

# ---------------------------------------------------------------------------
# CAN bus
# ---------------------------------------------------------------------------
print(f"[INIT] Opening SocketCAN bus on '{can_rx.BUS_CHANNEL}'...")
BUS = can.interface.Bus(channel=can_rx.BUS_CHANNEL, bustype="socketcan")
print("[INIT] Bus is up. Starting RX thread...")
can_rx.start(BUS)

# ---------------------------------------------------------------------------
# Pygame
# ---------------------------------------------------------------------------
pygame.init()
W, H = 800, 480
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("NFS Dashboard")
clock = pygame.display.flip and pygame.time.Clock()
clock = pygame.time.Clock()

# ---------------------------------------------------------------------------
# Screen registry
# ---------------------------------------------------------------------------
tc_screen = TCScreen(bus=BUS)
startup_screen = StartupScreen()  # ← NEW

screens: dict = {
    "startup": startup_screen,  # ← NEW
    "dashboard": DashboardScreen(),
    "menu": MenuScreen(),
    "tc": tc_screen,
}
current: str = "startup"  # ← start here, not dashboard

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
print("[INIT] UI loop started. Beginning startup sequence.")
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            continue
        result = screens[current].handle_event(event)
        if result and result in screens:
            print(f"[NAV] {current} → {result}")
            current = result

    # ── Startup screen auto-navigation ─────────────────────────────────────
    # StartupScreen signals completion via a property rather than an event,
    # because the transition is time-driven (TSAL blink count), not input-driven.
    if current == "startup" and startup_screen.wants_dashboard:
        print("[NAV] startup → dashboard (sequence complete)")
        current = "dashboard"

    screens[current].draw(screen, can_rx.latest)
    pygame.display.flip()
    clock.tick(30)

pygame.quit()
print("[EXIT] Dashboard closed.")
