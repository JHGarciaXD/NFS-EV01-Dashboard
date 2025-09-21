#!/usr/bin/env python3
import time, math, random
import can

# ======= CAN IDs (must match the dashboard) =======
ID_PEDAL = 0x101   # [apps_u8, brake_u8, status, ctr]
ID_SPEED = 0x110   # [speed_kph, 0, ctr, 0]
ID_BATT  = 0x111   # [soc%, pack_temp_C, 0, ctr]
ID_TEMPS = 0x112   # [water_temp_C, inv_temp_C, 0, ctr]
ID_HB    = 0x102   # [uptime32le, fw_tag, 0, 0]

# ======= SocketCAN bus on vcan0 =======
bus = can.interface.Bus(channel="vcan0", bustype="socketcan")

# ======= Counters (per-ID rolling 0..15) =======
ctr = {ID_PEDAL:0, ID_SPEED:0, ID_BATT:0, ID_TEMPS:0}
def roll(id_):
    ctr[id_] = (ctr[id_] + 1) & 0x0F
    return ctr[id_]

def bump_by(id_, step):
    ctr[id_] = (ctr[id_] + step) & 0x0F
    return ctr[id_]

def clamp(v, lo, hi): 
    return max(lo, min(hi, v))

# ======= Scenario scheduler =======
"""
30-second loop of scenarios:

  0–5s   : Normal driving
  5–10s  : Brake–throttle overlap (sets status bit)
  10–12s : CAN stall for Pedal (no 0x101 for ~2s) -> tests UI still OK (no counter err)
  12–15s : Counter jump on Pedal (roll by +2 once) -> should trip CAN quality on your side
  15–20s : Temperature spikes/out-of-range blips (clamped) + noise
  20–25s : Battery sag from ~85% to ~20%, then small recovery
  25–30s : Speed high-load burst + jitter

Repeats.
"""

def phase(t):
    # return current phase name and local time within phase
    T = 30.0
    tt = t % T
    if tt < 5.0:   return "normal",            tt
    if tt < 10.0:  return "overlap",           tt-5.0
    if tt < 12.0:  return "can_stall",         tt-10.0
    if tt < 15.0:  return "counter_jump",      tt-12.0
    if tt < 20.0:  return "temp_spike",        tt-15.0
    if tt < 25.0:  return "battery_sag",       tt-20.0
    # 25–30
    return "speed_burst", tt-25.0

t0 = time.time()
last_pedal_sent = 0.0
did_jump_this_phase = False

def reset_phase_flags():
    global did_jump_this_phase
    did_jump_this_phase = False

while True:
    t = time.time() - t0
    ph, pt = phase(t)
    # reset one-shot flags on phase boundary
    if abs((t % 30.0) - 0.0) < 0.02:  # near wrap
        reset_phase_flags()

    # ---------- Base signals (continuous) ----------
    # APPS% baseline: 0..100 slow sine
    apps_pct = (math.sin(2*math.pi*0.15*t)*0.5 + 0.5) * 100.0
    # Brake% baseline: triangle 0..100 every 3s
    tri = abs((t % 3.0) - 1.5) / 1.5
    brake_pct = tri * 100.0
    # Status bits (bit0 = generic fault; bit1 = overlap)
    status = 0x00
    # Speed baseline: 0..160 kph wave
    speed = (math.sin(2*math.pi*0.05*t)*0.5 + 0.5) * 160.0
    # SOC baseline: ~60–85%
    soc = 72 + 12*math.sin(2*math.pi*0.01*t)
    # Temps baseline (°C)
    pack_temp  = 35 + 5*math.sin(2*math.pi*0.02*t) + random.uniform(-0.4, 0.4)
    water_temp = 60 + 10*math.sin(2*math.pi*0.03*t + 1.3) + random.uniform(-0.5,0.5)
    inv_temp   = 55 + 8*math.sin(2*math.pi*0.025*t + 0.7) + random.uniform(-0.5,0.5)

    # ---------- Scenario modifications ----------
    if ph == "normal":
        pass

    elif ph == "overlap":
        # force meaningful overlap: brake > 20% while apps > 20%
        apps_pct = 60 + 35*math.sin(2*math.pi*0.6*pt)   # keep throttle high-ish
        brake_pct = 40 + 30*math.sin(2*math.pi*0.8*pt + 1.1)
        status |= 0x02  # your dash can treat this as "overlap fault" if desired

    elif ph == "can_stall":
        # stop sending the PEDAL frame entirely for ~2s
        # others still flow; this *won't* trigger a counter mismatch (since no frame)
        pass

    elif ph == "counter_jump":
        # once per phase, jump the 0x101 counter by +2 to emulate a drop/dup
        if not did_jump_this_phase:
            bump_by(ID_PEDAL, 1)   # extra advance (next roll will add +1 again)
            did_jump_this_phase = True
        # pump signals normally

    elif ph == "temp_spike":
        # inject occasional spikes (will be clamped on send)
        if pt < 1.0:
            pack_temp  = 95 + 10*random.random()
            water_temp = 105 + 15*random.random()
            inv_temp   = 95 + 12*random.random()
            status |= 0x01  # generic fault blip
        else:
            # noisy cooling afterwards
            water_temp += 5*math.sin(2*math.pi*2.0*pt)

    elif ph == "battery_sag":
        # drain SOC down then slight recovery
        sag = max(0.0, 20.0*pt)     # 0 → 100 over 5s scaled to ~20%
        soc = clamp(85.0 - sag, 10.0, 100.0)
        pack_temp += 3.0*pt  # slow heat rise

    elif ph == "speed_burst":
        # slam to high speed with jitter
        speed = 130 + 25*math.sin(2*math.pi*0.9*pt) + random.uniform(-3,3)
        apps_pct = clamp(70 + 25*math.sin(2*math.pi*1.2*pt), 0, 100)
        brake_pct = clamp(5 + 5*math.sin(2*math.pi*1.7*pt + 2.0), 0, 100)

    # ---------- Build payloads ----------
    apps_u8  = int(clamp(apps_pct,  0, 100) * 255/100)
    brake_u8 = int(clamp(brake_pct, 0, 100) * 255/100)
    speed_u8 = int(clamp(speed, 0, 255))
    soc_u8   = int(clamp(soc, 0, 100))

    # temps: clamp to -40..215C then encode as unsigned 0..255
    def enc_temp_c(v):
        return int(clamp(v, -40, 215)) & 0xFF

    # ---------- Transmit (with varied rates) ----------
    now = time.time()

    # PEDAL @100 Hz, except during can_stall phase (skip sends)
    if ph != "can_stall":
        data = bytes([apps_u8, brake_u8, status, roll(ID_PEDAL)])
        bus.send(can.Message(arbitration_id=ID_PEDAL, data=data, is_extended_id=False))

    # SPEED @50 Hz
    if int(t*50) != int((t-0.01)*50):
        data = bytes([speed_u8, 0x00, roll(ID_SPEED), 0x00])
        bus.send(can.Message(arbitration_id=ID_SPEED, data=data, is_extended_id=False))

    # BATT @10 Hz
    if int(t*10) != int((t-0.01)*10):
        data = bytes([soc_u8, enc_temp_c(pack_temp), 0x00, roll(ID_BATT)])
        bus.send(can.Message(arbitration_id=ID_BATT, data=data, is_extended_id=False))

    # TEMPS @10 Hz
    if int(t*10) != int((t-0.01)*10):
        data = bytes([enc_temp_c(water_temp), enc_temp_c(inv_temp), 0x00, roll(ID_TEMPS)])
        bus.send(can.Message(arbitration_id=ID_TEMPS, data=data, is_extended_id=False))

    # HEARTBEAT @5 Hz
    if int(t*5) != int((t-0.01)*5):
        up = int(time.time() - t0)
        hb = bytes([up & 0xFF, (up>>8)&0xFF, (up>>16)&0xFF, (up>>24)&0xFF, 0x11, 0, 0, 0])
        bus.send(can.Message(arbitration_id=ID_HB, data=hb, is_extended_id=False))

    # small base sleep; rates above are governed by the if-conditions
    time.sleep(0.01)
