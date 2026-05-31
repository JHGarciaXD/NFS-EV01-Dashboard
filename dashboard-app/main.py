"""
main.py
Entry point for the FS Dashboard.

Run with:
    python main.py
"""

import pygame
import can

import can_rx
from ui.dashboard import DashboardScreen
from ui.menu      import MenuScreen
from ui.tc        import TCScreen

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
W, H   = 800, 480
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("FS Dashboard")
clock  = pygame.time.Clock()

# ---------------------------------------------------------------------------
# Screen registry
# ---------------------------------------------------------------------------
tc_screen = TCScreen(bus=BUS)   # give TC direct access to the bus for sending

screens: dict = {
    "dashboard": DashboardScreen(),
    "menu":      MenuScreen(),
    "tc":        tc_screen,
}
current: str = "dashboard"

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
print("[INIT] UI loop started.")
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

    screens[current].draw(screen, can_rx.latest)
    pygame.display.flip()
    clock.tick(30)

pygame.quit()
print("[EXIT] Dashboard closed.")