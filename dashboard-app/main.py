import threading, time
import pygame
import can

BUS_CHANNEL = "vcan0"   # change to "can0" on the Pi later
BUS = can.interface.Bus(channel=BUS_CHANNEL, bustype="socketcan")

latest = {
    "apps_pct": 0.0,
    "brake_pct": 0.0,
    "status_bits": 0,
    "can_counter_ok": True,
}
_last_counter = None

def can_rx_loop():
    global _last_counter
    while True:
        msg = BUS.recv(timeout=1.0)
        if msg is None:
            continue
        if msg.arbitration_id == 0x101 and len(msg.data) >= 4:
            apps = msg.data[0] / 255.0 * 100.0
            brake = msg.data[1] / 255.0 * 100.0
            status = msg.data[2]
            counter = msg.data[3] & 0x0F
            if _last_counter is not None and ((counter - _last_counter) & 0x0F) != 1:
                latest["can_counter_ok"] = False
            else:
                latest["can_counter_ok"] = True
            _last_counter = counter
            latest["apps_pct"] = apps
            latest["brake_pct"] = brake
            latest["status_bits"] = status

rx_thread = threading.Thread(target=can_rx_loop, daemon=True)
rx_thread.start()

pygame.init()
W, H = 800, 480
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("FS Dashboard (Week 1)")
clock = pygame.time.Clock()
FONT_BIG = pygame.font.SysFont("DejaVu Sans", 72)
FONT_MED = pygame.font.SysFont("DejaVu Sans", 28)

def draw_bar(x, y, w, h, pct, label):
    pygame.draw.rect(screen, (230,230,230), (x,y,w,h))
    fill_w = int(w * max(0,min(100,pct))/100.0)
    pygame.draw.rect(screen, (50,50,50), (x,y,fill_w,h))
    pygame.draw.rect(screen, (10,10,10), (x,y,w,h), 3)
    txt = FONT_MED.render(f"{label}: {pct:.0f}%", True, (10,10,10))
    screen.blit(txt, (x, y - 32))

def draw_banner(text, color):
    surf = FONT_BIG.render(text, True, color)
    rect = surf.get_rect(center=(W//2, 70))
    screen.blit(surf, rect)

running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

    screen.fill((255,255,255))  # bright background for daylight

    draw_bar(80, 180, 640, 50, latest["apps_pct"], "APPS")
    draw_bar(80, 280, 640, 50, latest["brake_pct"], "Brake")

    if latest["status_bits"] != 0:
        draw_banner("FAULT", (200,0,0))
    elif not latest["can_counter_ok"]:
        draw_banner("CAN DROP", (200,100,0))
    else:
        draw_banner("OK", (0,120,0))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
