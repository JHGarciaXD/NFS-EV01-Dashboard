import threading
import time

import can

# ===== CAN message map (custom) =====
# 0x101 Pedal_Processed:  [0]=APPS% (0-255), [1]=Brake% (0-255), [2]=StatusBits, [3]=Counter(0..15)
# 0x110 Vehicle_Speed:    [0]=Speed_kph (0-255), [1]=reserved, [2]=Counter, [3]=reserved
# 0x111 Battery_State:    [0]=SOC% (0-100), [1]=PackTemp_C (0..255 for now), [2]=reserved, [3]=Counter
# 0x112 Temps_Misc:       [0]=WaterTemp_C, [1]=InverterTemp_C, [2]=reserved, [3]=Counter
# 0x102 Heartbeat:        [0..3]=Uptime seconds (LSB first), [4]=FW tag (8-bit), [5..7]=reserved
# 0x120 TC_Command (TX):  [0]=TC level (1..10), [1]=0x01 magic, [2..7]=reserved
ID_PEDAL = 0x101
ID_SPEED = 0x110
ID_BATT = 0x111
ID_TEMPS = 0x112
ID_HB = 0x102

D_M161 = 0xA1  # Cascadia hot spot motor
ID_M162 = 0xA2  # Cascadia hot spot inverter


BUS_CHANNEL = "vcan0"  # change to "can0" on the Pi

latest = {
    "apps_pct": 0.0,
    "brake": 0.0,
    "status_bits": 0,
    "can_counter_ok": True,
    "battery": 0.0,  # SOC %
    "speed": 0.0,  # kph
    "battery_temp": 0.0,  # °C
    "water_temp": 0.0,  # °C
    "inv_temp": 0.0,  # °C
    "uptime": 0,  # seconds
}

_last_counters = {}
_last_log_time = {
    ID_PEDAL: 0.0,
    ID_SPEED: 0.0,
    ID_BATT: 0.0,
    ID_TEMPS: 0.0,
    ID_HB: 0.0,
}
_LOG_INTERVAL = {
    ID_PEDAL: 0.25,
    ID_SPEED: 0.30,
    ID_BATT: 0.60,
    ID_TEMPS: 0.60,
    ID_HB: 1.00,
}


summary_last = 0.0
summary_interval = 1.0  # 1 Hz


_temp_handler = None


def register_temp_handler(fn):
    """Call once from main.py to route temp-relevant frames to TempService."""
    global _temp_handler
    _temp_handler = fn


def _check_counter(arbid: int, ctr: int) -> bool:
    prev = _last_counters.get(arbid)
    ok = True
    if prev is not None and ((ctr - prev) & 0x0F) != 1:
        ok = False
        print(
            f"[WARN] Counter jump on 0x{arbid:03X}: prev={prev} now={ctr} (expected +1)"
        )
    _last_counters[arbid] = ctr & 0x0F
    return ok


def _throttled(arbid: int) -> bool:
    now = time.time()
    last = _last_log_time.get(arbid, 0.0)
    if now - last >= _LOG_INTERVAL.get(arbid, 0.5):
        _last_log_time[arbid] = now
        return True
    return False


def can_rx_loop(bus: can.BusABC) -> None:
    global summary_last
    while True:
        msg = bus.recv(timeout=1.0)
        if msg is None:
            continue

        try:
            if msg.arbitration_id == ID_PEDAL and len(msg.data) >= 4:
                apps = msg.data[0] * 100.0 / 255.0
                brake = msg.data[1] * 100.0 / 255.0
                stat = msg.data[2]
                ctr = msg.data[3] & 0x0F

                latest["apps_pct"] = apps
                latest["brake"] = brake
                latest["status_bits"] = stat
                ok = _check_counter(ID_PEDAL, ctr)
                latest["can_counter_ok"] = latest["can_counter_ok"] and ok

                if _throttled(ID_PEDAL):
                    print(
                        f"[101 PEDAL] APPS={apps:5.1f}%  Brake={brake:5.1f}%  "
                        f"Stat=0x{stat:02X} Ctr={ctr} OK={ok}"
                    )

            elif msg.arbitration_id == ID_SPEED and len(msg.data) >= 3:
                spd = msg.data[0]
                ctr = msg.data[2] & 0x0F
                latest["speed"] = float(spd)
                ok = _check_counter(ID_SPEED, ctr)
                latest["can_counter_ok"] = latest["can_counter_ok"] and ok

                if _throttled(ID_SPEED):
                    print(f"[110 SPEED] {spd:3d} km/h  Ctr={ctr} OK={ok}")

            elif msg.arbitration_id == ID_BATT and len(msg.data) >= 4:
                soc = msg.data[0]
                temp = msg.data[1]
                ctr = msg.data[3] & 0x0F
                latest["battery"] = float(soc)
                latest["battery_temp"] = float(temp)
                ok = _check_counter(ID_BATT, ctr)
                latest["can_counter_ok"] = latest["can_counter_ok"] and ok

                if _throttled(ID_BATT):
                    print(
                        f"[111 BATT ] SOC={soc:3d}%  PackTemp={temp:3d}°C  Ctr={ctr} OK={ok}"
                    )

            elif msg.arbitration_id == ID_TEMPS and len(msg.data) >= 4:
                water = msg.data[0]
                inv = msg.data[1]
                ctr = msg.data[3] & 0x0F
                latest["water_temp"] = float(water)
                latest["inv_temp"] = float(inv)
                ok = _check_counter(ID_TEMPS, ctr)
                latest["can_counter_ok"] = latest["can_counter_ok"] and ok

                if _throttled(ID_TEMPS):
                    print(
                        f"[112 TEMPS] Water={water:3d}°C  Inverter={inv:3d}°C  Ctr={ctr} OK={ok}"
                    )

            elif msg.arbitration_id == ID_HB and len(msg.data) >= 5:
                up = (
                    msg.data[0]
                    | (msg.data[1] << 8)
                    | (msg.data[2] << 16)
                    | (msg.data[3] << 24)
                )
                latest["uptime"] = up

                if _throttled(ID_HB):
                    print(f"[102 HB   ] Uptime={up:6d}s FW=0x{msg.data[4]:02X}")

            # In can_rx_loop(), add these two blocks alongside the existing elif chain:

            elif msg.arbitration_id == 0x120 and len(msg.data) >= 7:
                # Temp controller Arduino → RPi
                # Handled by TempService directly; we just forward it.
                if _temp_handler is not None:
                    _temp_handler(msg)

            elif msg.arbitration_id == 0x162 and len(msg.data) >= 8:
                # Cascadia M162: Motor + Inverter + Coolant temps (0.1°C scale, int16 LE)
                motor_raw = int.from_bytes(msg.data[4:6], "little", signed=True)
                inv_raw = int.from_bytes(msg.data[2:4], "little", signed=True)
                coolant_raw = int.from_bytes(msg.data[0:2], "little", signed=True)
                latest["motor_temp"] = motor_raw * 0.1
                latest["inv_temp"] = inv_raw * 0.1
                latest["coolant_temp"] = coolant_raw * 0.1

            # 1 Hz summary
            now = time.time()
            if now - summary_last >= summary_interval:
                summary_last = now
                print(
                    "  ── SUMMARY ───────────────────────────────────────────────────"
                )
                print(
                    f"    APPS={latest['apps_pct']:5.1f}%  Brake={latest['brake']:5.1f}%"
                    f"  Speed={latest['speed']:5.1f} km/h  SOC={latest['battery']:3.0f}%"
                )
                print(
                    f"    Temps → Pack={latest['battery_temp']:3.0f}°C  "
                    f"Water={latest['water_temp']:3.0f}°C  Inverter={latest['inv_temp']:3.0f}°C"
                )
                print(
                    f"    StatusBits=0x{latest['status_bits']:02X}  "
                    f"CAN_OK={latest['can_counter_ok']}  Uptime={latest['uptime']}s"
                )
                print(
                    "  ──────────────────────────────────────────────────────────────"
                )

        except Exception as e:
            print(
                f"[ERROR] Failed to parse frame 0x{msg.arbitration_id:03X} ({msg}): {e}"
            )

        time.sleep(0.001)


def start(bus: can.BusABC) -> threading.Thread:
    """Spawn and return the daemon RX thread."""
    t = threading.Thread(target=can_rx_loop, args=(bus,), daemon=True)
    t.start()
    return t
