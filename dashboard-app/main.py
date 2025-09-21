import threading, time
import pygame
import can

# ===== CAN message map (custom) =====
# 0x101 Pedal_Processed:  [0]=APPS% (0-255), [1]=Brake% (0-255), [2]=StatusBits, [3]=Counter(0..15)
# 0x110 Vehicle_Speed:    [0]=Speed_kph (0-255), [1]=reserved, [2]=Counter, [3]=reserved
# 0x111 Battery_State:    [0]=SOC% (0-100), [1]=PackTemp_C (0..255 for now), [2]=reserved, [3]=Counter
# 0x112 Temps_Misc:       [0]=WaterTemp_C, [1]=InverterTemp_C, [2]=reserved, [3]=Counter
# 0x102 Heartbeat:        [0..3]=Uptime seconds (LSB first), [4]=FW tag (8-bit), [5..7]=reserved
ID_PEDAL   = 0x101
ID_SPEED   = 0x110
ID_BATT    = 0x111
ID_TEMPS   = 0x112
ID_HB      = 0x102

# ===== CAN setup =====
BUS_CHANNEL = "vcan0"  # change to "can0" on the Pi
print(f"[INIT] Opening SocketCAN bus on '{BUS_CHANNEL}'...")
BUS = can.interface.Bus(channel=BUS_CHANNEL, bustype="socketcan")
print("[INIT] Bus is up. Waiting for frames...")

latest = {
    "apps_pct": 0.0,
    "brake": 0.0,
    "status_bits": 0,
    "can_counter_ok": True,

    "battery": 0.0,        # SOC %
    "speed": 0.0,          # kph
    "battery_temp": 0.0,   # °C
    "water_temp": 0.0,     # °C
    "inv_temp": 0.0,       # °C

    "uptime": 0,           # seconds
}
_last_counters = {}  # per-ID rolling counters to detect drops
_last_log_time = {   # per-ID log throttling
    ID_PEDAL: 0.0,   # log every ~0.25s
    ID_SPEED: 0.0,   # ~0.3s
    ID_BATT:  0.0,   # ~0.6s
    ID_TEMPS: 0.0,   # ~0.6s
    ID_HB:    0.0,   # ~1.0s
}
_LOG_INTERVAL = {
    ID_PEDAL: 0.25,
    ID_SPEED: 0.30,
    ID_BATT:  0.60,
    ID_TEMPS: 0.60,
    ID_HB:    1.00,
}
summary_last = 0.0
summary_interval = 1.0  # 1 Hz summary

def _check_counter(arbid: int, ctr: int):
    prev = _last_counters.get(arbid)
    ok = True
    if prev is not None and ((ctr - prev) & 0x0F) != 1:
        ok = False
        print(f"[WARN] Counter jump on 0x{arbid:03X}: prev={prev} now={ctr} (expected +1)")
    _last_counters[arbid] = ctr & 0x0F
    return ok

def _throttled(arbid: int) -> bool:
    """Return True if it's time to print for this arbid."""
    now = time.time()
    last = _last_log_time.get(arbid, 0.0)
    if now - last >= _LOG_INTERVAL.get(arbid, 0.5):
        _last_log_time[arbid] = now
        return True
    return False

def can_rx_loop():
    global summary_last
    while True:
        msg = BUS.recv(timeout=1.0)
        if msg is None:
            continue

        try:
            if msg.arbitration_id == ID_PEDAL and len(msg.data) >= 4:
                apps  = msg.data[0] * 100.0 / 255.0
                brake = msg.data[1] * 100.0 / 255.0
                stat  = msg.data[2]
                ctr   = msg.data[3] & 0x0F

                latest["apps_pct"] = apps
                latest["brake"] = brake
                latest["status_bits"] = stat
                ok = _check_counter(ID_PEDAL, ctr)
                latest["can_counter_ok"] = latest["can_counter_ok"] and ok

                if _throttled(ID_PEDAL):
                    print(f"[101 PEDAL] APPS={apps:5.1f}%  Brake={brake:5.1f}%  "
                          f"Stat=0x{stat:02X} Ctr={ctr} OK={ok}")

            elif msg.arbitration_id == ID_SPEED and len(msg.data) >= 3:
                spd = msg.data[0]  # kph 0..255
                ctr = msg.data[2] & 0x0F
                latest["speed"] = float(spd)
                ok = _check_counter(ID_SPEED, ctr)
                latest["can_counter_ok"] = latest["can_counter_ok"] and ok

                if _throttled(ID_SPEED):
                    print(f"[110 SPEED] {spd:3d} km/h  Ctr={ctr} OK={ok}")

            elif msg.arbitration_id == ID_BATT and len(msg.data) >= 4:
                soc = msg.data[0]
                temp = msg.data[1]  # treat as unsigned 0..255
                ctr = msg.data[3] & 0x0F
                latest["battery"] = float(soc)
                latest["battery_temp"] = float(temp)
                ok = _check_counter(ID_BATT, ctr)
                latest["can_counter_ok"] = latest["can_counter_ok"] and ok

                if _throttled(ID_BATT):
                    print(f"[111 BATT ] SOC={soc:3d}%  PackTemp={temp:3d}°C  Ctr={ctr} OK={ok}")

            elif msg.arbitration_id == ID_TEMPS and len(msg.data) >= 4:
                water = msg.data[0]
                inv   = msg.data[1]
                ctr   = msg.data[3] & 0x0F
                latest["water_temp"] = float(water)
                latest["inv_temp"] = float(inv)
                ok = _check_counter(ID_TEMPS, ctr)
                latest["can_counter_ok"] = latest["can_counter_ok"] and ok

                if _throttled(ID_TEMPS):
                    print(f"[112 TEMPS] Water={water:3d}°C  Inverter={inv:3d}°C  Ctr={ctr} OK={ok}")

            elif msg.arbitration_id == ID_HB and len(msg.data) >= 5:
                up = (msg.data[0] |
                      (msg.data[1]<<8) |
                      (msg.data[2]<<16) |
                      (msg.data[3]<<24))
                latest["uptime"] = up

                if _throttled(ID_HB):
                    print(f"[102 HB   ] Uptime={up:6d}s FW=0x{msg.data[4]:02X}")

            # ---- 1 Hz summary of all key values ----
            now = time.time()
            if now - summary_last >= summary_interval:
                summary_last = now
                print("  ── SUMMARY ───────────────────────────────────────────────────")
                print(f"    APPS={latest['apps_pct']:5.1f}%  Brake={latest['brake']:5.1f}%"
                      f"  Speed={latest['speed']:5.1f} km/h  SOC={latest['battery']:3.0f}%")
                print(f"    Temps → Pack={latest['battery_temp']:3.0f}°C  "
                      f"Water={latest['water_temp']:3.0f}°C  Inverter={latest['inv_temp']:3.0f}°C")
                print(f"    StatusBits=0x{latest['status_bits']:02X}  "
                      f"CAN_OK={latest['can_counter_ok']}  Uptime={latest['uptime']}s")
                print("  ──────────────────────────────────────────────────────────────")

        except Exception as e:
            print(f"[ERROR] Failed to parse frame 0x{msg.arbitration_id:03X} ({msg}): {e}")
        # tiny sleep prevents tight-loop spin if something floods
        time.sleep(0.001)

rx_thread = threading.Thread(target=can_rx_loop, daemon=True)
rx_thread.start()

# ===== UI (Pygame) =====
pygame.init()
W, H = 800, 480
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("FS Dashboard — Custom CAN (with logs)")
clock = pygame.time.Clock()

# Fonts
FONT_BIG    = pygame.font.SysFont("DejaVu Sans", 120, bold=True)
FONT_MED    = pygame.font.SysFont("DejaVu Sans", 28,  bold=True)
FONT_MID    = pygame.font.SysFont("DejaVu Sans Mono", 16)
FONT_SMALL  = pygame.font.SysFont("DejaVu Sans Mono", 12)
# 7-segment look (ensure these files exist)
FONT_DIGITAL         = pygame.font.Font("assets/fonts/DSEG14Classic-Bold.ttf", 100)
FONT_DIGITAL_MED     = pygame.font.Font("assets/fonts/DSEG14Classic-Bold.ttf", 70)
FONT_DIGITAL_SMALLER = pygame.font.Font("assets/fonts/DSEG14Classic-Bold.ttf", 30)

# Theme + dark mode toggle
LIGHT = {
    "screen_bg": (255, 255, 255),
    "panel_bg":  (255, 255, 255),
    "fill_bg":   (230, 230, 230),
    "border":    (10, 10, 10),
    "text":      (0, 0, 0),
    "ok":        (0, 100, 0),
    "warn":      (200, 100, 0),
    "err":       (200, 0, 0),
    "button_bg": (235, 235, 235),
    "button_fg": (0, 0, 0),
}
DARK = {
    "screen_bg": (15, 15, 18),
    "panel_bg":  (28, 28, 32),
    "fill_bg":   (38, 38, 44),
    "border":    (200, 200, 200),
    "text":      (240, 240, 240),
    "ok":        (80, 220, 120),
    "warn":      (255, 170, 40),
    "err":       (255, 80, 80),
    "button_bg": (55, 55, 65),
    "button_fg": (240, 240, 240),
}
dark_mode = False
def T(): return DARK if dark_mode else LIGHT
BTN_RECT = pygame.Rect(655, 355, 90, 45)

def draw_darkmode_button():
    label = "Dark" if not dark_mode else "Light"
    pygame.draw.rect(screen, T()["button_bg"], BTN_RECT, border_radius=10)
    pygame.draw.rect(screen, T()["border"],    BTN_RECT, width=2, border_radius=10)
    txt = FONT_MED.render(label, True, T()["button_fg"])
    screen.blit(txt, txt.get_rect(center=BTN_RECT.center))

# Color helpers
def heat_color_inverted(pct: float):
    p = max(0, min(100, pct)) / 100.0
    bp = 0.3
    if p < bp:
        t = p / bp
        r = 255
        g = int(225 + 30 * (1 - t))
        b = int(255 * (1 - t))
    else:
        t = (p - bp) / (1 - bp)
        r = int(255 - 55 * t)
        g = int(255 * (1 - t))
        b = 0
    return (r, g, b)

def cool_color(pct: float):
    p = max(0, min(100, pct)) / 100.0
    r = int(255 * (1 - p))
    g = int(255 * (1 - p * 0.7))
    b = int(255 - 55 * p)
    return (r, g, b)

# Widgets
def draw_battery_bar(x, y, w, h, pct):
    pygame.draw.rect(screen, T()["fill_bg"], (x, y, w, h))
    if pct > 70:   fill_color = (0, 100, 0)
    elif pct > 50: fill_color = (0, 200, 0)
    elif pct > 35: fill_color = (255, 200, 0)
    elif pct > 20: fill_color = (255, 100, 0)
    else:          fill_color = (200, 0, 0)
    fill_w = int(w * max(0, min(100, pct)) / 100.0)
    pygame.draw.rect(screen, fill_color, (x, y, fill_w, h))
    pygame.draw.rect(screen, T()["border"], (x, y, w, h), 3)

def draw_rect_value(x, y, w, h, value, label=None):
    pygame.draw.rect(screen, T()["panel_bg"], (x, y, w, h), border_radius=20)
    pygame.draw.rect(screen, T()["border"],   (x, y, w, h), width=3, border_radius=20)
    txt = FONT_DIGITAL.render(f"{value:.0f}", True, T()["text"])
    screen.blit(txt, txt.get_rect(center=(x + (w * 0.47), y + h // 2)))
    if label:
        lbl = FONT_SMALL.render(label, True, T()["text"])
        screen.blit(lbl, lbl.get_rect(center=(x + w//2, y + 16)))

def draw_temp_box(x, y, w, h, temp, label):
    pygame.draw.rect(screen, T()["panel_bg"], (x, y, w, h), border_radius=20)
    pygame.draw.rect(screen, T()["border"],   (x, y, w, h), width=3, border_radius=20)
    txt = FONT_DIGITAL_SMALLER.render(f"{temp:.0f}º", True, T()["text"])
    screen.blit(txt, txt.get_rect(center=(x + (w * 0.47), y + h // 2)))
    lbl = FONT_SMALL.render(label, True, T()["text"])
    screen.blit(lbl, lbl.get_rect(center=(x + w // 2, y + 15)))

def draw_segment_bar(x, y, w, h, pct, mode="heat", segments=40, gap=1, border_radius=0):
    pygame.draw.rect(screen, T()["fill_bg"], (x, y, w, h), border_radius=border_radius)
    pygame.draw.rect(screen, T()["border"],  (x, y, w, h), width=3, border_radius=border_radius)
    p = max(0, min(100, pct)) / 100.0
    total_gap = gap * (segments - 1)
    seg_h = max(1, (h - total_gap) // segments)
    lit_full = int(p * segments)
    for i in range(segments):
        seg_bottom = y + h - (i + 1) * seg_h - i * gap + gap
        rect = pygame.Rect(x, seg_bottom, w, seg_h)
        rel = (i + 0.5) / segments
        col = heat_color_inverted(rel * 100.0) if mode == "heat" else cool_color(rel * 100.0)
        if i < lit_full:
            pygame.draw.rect(screen, col, rect, border_radius=border_radius // 2)
        else:
            pygame.draw.rect(screen, (210, 210, 210), rect, border_radius=border_radius // 2)
        pygame.draw.rect(screen, T()["border"], rect, width=1, border_radius=border_radius // 2)

def draw_banner(text, color):
    surf = FONT_DIGITAL_MED.render(text, True, color)
    rect = surf.get_rect(center=(W // 2, 60))
    screen.blit(surf, rect)

# Main loop
running = True
print("[INIT] UI loop started. Click the bottom-left button to toggle Dark/Light mode.")
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if BTN_RECT.collidepoint(e.pos):
                dark_mode = not dark_mode
                latest["can_counter_ok"] = True  # visual reset
                print(f"[THEME] Dark mode set to {dark_mode}")

    screen.fill(T()["screen_bg"])

    # Layout
    draw_battery_bar(0,   405, 800, 75, latest["battery"])
    draw_rect_value(265, 115, 270, 230, latest["speed"], "Speed")
    draw_temp_box(140, 115, 105, 105, latest["battery_temp"], "Battery temp")
    draw_segment_bar(0,   0, 50, 405, latest["apps_pct"], mode="heat")     # APPS
    draw_segment_bar(750, 0, 50, 405, latest["brake"],    mode="cool")     # Brake
    draw_temp_box(140, 240, 105, 105, latest["water_temp"], "Water temp")
    draw_temp_box(560, 115, 105, 105, latest["inv_temp"],   "Inverter temp")

    # Banner
    if latest["status_bits"] != 0:
        draw_banner("FAULT", T()["err"])
    elif not latest["can_counter_ok"]:
        draw_banner("CAN DROP", T()["warn"])
    else:
        draw_banner("OK", T()["ok"])

    draw_darkmode_button()

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
print("[EXIT] Dashboard closed.")
