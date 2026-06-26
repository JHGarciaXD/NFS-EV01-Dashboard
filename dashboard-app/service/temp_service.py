"""
services/temp_service.py
Temperature logic — Motor & Inverter channels.

CAN frame map:
  RX 0xA1 (M161) → INV_Hot_Spot_Temp_Motor     bytes [6:7] int16 LE x0.1 °C
  RX 0xA2 (M162) → INV_Hot_Spot_Temp_Inverter  bytes [2:3] int16 LE x0.1 °C
  RX 0x120       → Arduino status (NTC temps, fan states, faults)
  TX 0x130       → threshold config + force-on mask to Arduino
                   [0] motor threshold °C
                   [1] inverter threshold °C
                   [2] force bitmask (bit0=motor, bit1=inv)
                   [3..7] reserved

Indexes: 0 = Motor, 1 = Inverter
"""

import threading
import time

import can

CAN_ID_M161 = 0xA1
CAN_ID_M162 = 0xA2
CAN_ID_RX_STATUS = 0x120
CAN_ID_TX_CONFIG = 0x130

CH_MOTOR = 0
CH_INV = 1
NUM_CH = 2

THRESHOLD_MIN = 20
THRESHOLD_MAX = 150
THRESHOLD_DEF = 50


class TempService:
    """Thread-safe. UI reads public attrs; CAN RX thread calls on_can_frame()."""

    def __init__(self, bus: can.BusABC):
        self._bus = bus
        self._lock = threading.Lock()

        self.analog_temp: list[float] = [-99.0] * NUM_CH
        self.can_temp: list[float] = [-99.0] * NUM_CH
        self.fan_state: list[bool] = [False] * NUM_CH
        self.fan_forced: list[bool] = [False] * NUM_CH  # force-on per channel
        self.fault_mask: int = 0xFF
        self.thresholds: list[float] = [float(THRESHOLD_DEF)] * NUM_CH
        self._last_rx: float = 0.0

    # ── CAN RX ────────────────────────────────────────────────
    def on_can_frame(self, msg: can.Message) -> None:
        aid = msg.arbitration_id

        if aid == CAN_ID_RX_STATUS and msg.dlc >= 6:
            d = msg.data
            analog = [float(d[i]) - 50.0 for i in range(NUM_CH)]
            fans = [(d[4] >> i) & 1 == 1 for i in range(NUM_CH)]
            faults = d[5]
            with self._lock:
                self.analog_temp = analog
                self.fan_state = fans
                self.fault_mask = faults
                self._last_rx = time.monotonic()

        elif aid == CAN_ID_M161 and msg.dlc >= 8:
            raw = int.from_bytes(msg.data[6:8], "little", signed=True)
            with self._lock:
                self.can_temp[CH_MOTOR] = raw * 0.1

        elif aid == CAN_ID_M162 and msg.dlc >= 4:
            raw = int.from_bytes(msg.data[2:4], "little", signed=True)
            with self._lock:
                self.can_temp[CH_INV] = raw * 0.1

    # ── Force-on toggle ───────────────────────────────────────
    def toggle_force(self, channel: int) -> None:
        """Toggle fan force-on for one channel and push to Arduino."""
        if not (0 <= channel < NUM_CH):
            return
        with self._lock:
            self.fan_forced[channel] = not self.fan_forced[channel]
            thresh_copy = list(self.thresholds)
            forced_copy = list(self.fan_forced)
        self._send_config(thresh_copy, forced_copy)
        state = "ON" if forced_copy[channel] else "OFF"
        print(f"[TempService] Force ch{channel} → {state}")

    # ── Threshold management ──────────────────────────────────
    def adjust_threshold(self, channel: int, delta: float) -> None:
        if not (0 <= channel < NUM_CH):
            return
        with self._lock:
            val = max(
                THRESHOLD_MIN, min(THRESHOLD_MAX, self.thresholds[channel] + delta)
            )
            self.thresholds[channel] = val
            thresh_copy = list(self.thresholds)
            forced_copy = list(self.fan_forced)
        self._send_config(thresh_copy, forced_copy)

    def _send_config(self, thresholds: list[float], forced: list[bool]) -> None:
        """
        CAN 0x130 — 8 bytes:
          [0] motor threshold °C
          [1] inverter threshold °C
          [2] force bitmask (bit0=motor, bit1=inv)
          [3..7] 0x00
        """
        force_mask = 0
        for i, f in enumerate(forced):
            if f:
                force_mask |= 1 << i

        data = bytes([int(thresholds[0]), int(thresholds[1]), force_mask]) + bytes(5)
        msg = can.Message(
            arbitration_id=CAN_ID_TX_CONFIG, data=data, is_extended_id=False
        )
        try:
            self._bus.send(msg)
        except can.CanError as e:
            print(f"[TempService] CAN TX error: {e}")

    # ── Properties ───────────────────────────────────────────
    @property
    def is_stale(self) -> bool:
        return (time.monotonic() - self._last_rx) > 2.0

    def summary(self) -> dict:
        with self._lock:
            return {
                "temp_analog": list(self.analog_temp),
                "temp_can": list(self.can_temp),
                "temp_fan": list(self.fan_state),
                "temp_forced": list(self.fan_forced),
                "temp_thresh": list(self.thresholds),
                "temp_fault": self.fault_mask,
                "temp_stale": self.is_stale,
            }
