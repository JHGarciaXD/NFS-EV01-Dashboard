"""
service/tsal.py
───────────────
TSAL (Tractive System Active Light) state service.

Two inputs:  LV_ON, HV_ON  (GPIO or keyboard inject)
One output:  tsal_state  ->  "off" | "green" | "red_blink"
One GPIO output: relay pin pulses at 3 Hz when HV active

GPIO pins (BCM) — set before wiring:
  LV_PIN    = 17   input,  active HIGH
  HV_PIN    = 27   input,  active HIGH
  RELAY_PIN = 22   output, HIGH = relay energised
"""

RELAY_PIN = 22  # <── change this when wiring is confirmed
LV_PIN = 17
HV_PIN = 27

TSAL_BLINK_HZ = 3.0
TSAL_BLINK_MS = int(1000 / TSAL_BLINK_HZ / 2)  # half-period ms

try:
    import RPi.GPIO as GPIO

    _GPIO_AVAILABLE = True
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LV_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(HV_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)
except ImportError:
    _GPIO_AVAILABLE = False


class TSALService:
    """
    Call tick(now_ms) every frame.
    Read .state -> "off" | "green" | "red_blink"
    Read .relay_on -> bool (mirror of relay GPIO output)
    """

    def __init__(self):
        self._lv_on = False
        self._hv_on = False
        self._blink_on = False
        self._last_ms = 0

    # ── Keyboard / test inject ─────────────────────────────────────────────
    def inject_lv(self):
        self._lv_on = True

    def inject_hv(self):
        self._hv_on = True

    def inject_lv_off(self):
        self._lv_on = False
        self._hv_on = False  # HV can't be on without LV

    def inject_hv_off(self):
        self._hv_on = False

    # ── State ─────────────────────────────────────────────────────────────
    @property
    def state(self) -> str:
        if self._hv_on:
            return "red_blink"
        if self._lv_on:
            return "green"
        return "off"

    @property
    def relay_on(self) -> bool:
        return self._blink_on

    # ── tick ──────────────────────────────────────────────────────────────
    def tick(self, now_ms: int):
        self._poll_gpio()

        if self._hv_on:
            if now_ms - self._last_ms >= TSAL_BLINK_MS:
                self._blink_on = not self._blink_on
                self._last_ms = now_ms
                self._set_relay(self._blink_on)
        else:
            if self._blink_on:
                self._blink_on = False
                self._set_relay(False)

    # ── GPIO helpers ──────────────────────────────────────────────────────
    def _poll_gpio(self):
        if not _GPIO_AVAILABLE:
            return
        self._lv_on = bool(GPIO.input(LV_PIN))
        self._hv_on = bool(GPIO.input(HV_PIN))

    def _set_relay(self, on: bool):
        if not _GPIO_AVAILABLE:
            return
        GPIO.output(RELAY_PIN, GPIO.HIGH if on else GPIO.LOW)

    def cleanup(self):
        if _GPIO_AVAILABLE:
            self._set_relay(False)
            GPIO.cleanup()
