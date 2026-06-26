"""
main.py
"""

import can
import can_rx
import pygame
from services.temp_service import TempService
from ui.dashboard import DashboardScreen
from ui.menu import MenuScreen
from ui.startup import StartupScreen
from ui.tc import TCScreen
from ui.temp_control import TempControlScreen

# ---------------------------------------------------------------------------
# CAN bus
# ---------------------------------------------------------------------------
print(f"[INIT] Opening SocketCAN bus on '{can_rx.BUS_CHANNEL}'...")
BUS = can.interface.Bus(channel=can_rx.BUS_CHANNEL, bustype="socketcan")
print("[INIT] Bus is up. Starting RX thread...")
can_rx.start(BUS)

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
temp_svc = TempService(bus=BUS)  # ← only once
can_rx.register_temp_handler(temp_svc.on_can_frame)  # ← only once, here

# ---------------------------------------------------------------------------
# Pygame
# ---------------------------------------------------------------------------
pygame.init()
W, H = 800, 480
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("NFS Dashboard")
clock = pygame.time.Clock()

# ---------------------------------------------------------------------------
# Screen registry
# ---------------------------------------------------------------------------
tc_screen = TCScreen(bus=BUS)
startup_screen = StartupScreen()

screens: dict = {
    "startup": startup_screen,
    "dashboard": DashboardScreen(),
    "menu": MenuScreen(),
    "tc": tc_screen,
    "temp": TempControlScreen(bus=BUS, service=temp_svc),
}
current: str = "startup"

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

    if current == "startup" and startup_screen.wants_dashboard:
        print("[NAV] startup → dashboard (sequence complete)")
        current = "dashboard"

    can_rx.latest.update(temp_svc.summary())  # ← stays in loop, correct

    screens[current].draw(screen, can_rx.latest)
    pygame.display.flip()
    clock.tick(30)

pygame.quit()
print("[EXIT] Dashboard closed.")
