"""
main.py
"""

import can
import can_rx
import pygame
from service.temp_service import TempService
from service.tsal import TSALService
from ui.dashboard import DashboardScreen
from ui.menu import MenuScreen
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
temp_svc = TempService(bus=BUS)
can_rx.register_temp_handler(temp_svc.on_can_frame)
tsal_svc = TSALService()

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
screens: dict = {
    "dashboard": DashboardScreen(tsal=tsal_svc),
    "menu": MenuScreen(),
    "tc": TCScreen(bus=BUS),
    "temp": TempControlScreen(bus=BUS, service=temp_svc),
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
            print(f"[NAV] {current} -> {result}")
            current = result

    tsal_svc.tick(pygame.time.get_ticks())
    can_rx.latest.update(temp_svc.summary())
    screens[current].draw(screen, can_rx.latest)
    pygame.display.flip()
    clock.tick(30)

tsal_svc.cleanup()
pygame.quit()
print("[EXIT] Dashboard closed.")
