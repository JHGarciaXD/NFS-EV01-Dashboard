"""
service/tsal.py
---------------
TSAL (Tractive System Active Light) state service.

LV ON  -> TSAL green steady
HV ON  -> TSAL red blinking at 3 Hz + relay output pulses

GPIO pins (BCM):
  LV_PIN    = 17   input,  active HIGH  (LV key switch)
  HV_PIN    = 27   input,  active HIGH  (HV / TSMS switch)
  RELAY_PIN = 22   output, HIGH = relay energised  <- change when wiring confirmed
"""

LV_PIN = 17
HV_PIN = 27
RELAY_PIN = 22

TSAL_BLINK_HZ = 3.0
TSAL_BLINK_MS = int(1000 / TSAL_BLINK_HZ / 2)  # half-period in ms

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
    def __init__(self):
        self._lv_on = False
        self._hv_on = False
        self._blink_on = False
        self._last_ms = 0

    # -- Keyboard / test inject ---------------------------------------------
    def inject_lv(self):
        self._lv_on = True

    def inject_lv_off(self):
        self._lv_on = False
        self._hv_on = False  # HV can't exist without LV

    def inject_hv(self):
        self._hv_on = True

    def inject_hv_off(self):
        self._hv_on = False

    # -- State (read by ui/dashboard.py) ------------------------------------
    @property
    def state(self) -> str:
        """Returns 'off' | 'green' | 'red_blink'"""
        if self._hv_on:
            return "red_blink"
        if self._lv_on:
            return "green"
        return "off"

    @property
    def relay_on(self) -> bool:
        """True when relay is currently energised (blink HIGH phase)."""
        return self._blink_on

    # -- tick - called every frame from main.py -----------------------------
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

    # -- cleanup - call once on exit ----------------------------------------
    def cleanup(self):
        if _GPIO_AVAILABLE:
            self._set_relay(False)
            GPIO.cleanup()

    # -- Internal -----------------------------------------------------------
    def _poll_gpio(self):
        if not _GPIO_AVAILABLE:
            return
        self._lv_on = bool(GPIO.input(LV_PIN))
        self._hv_on = bool(GPIO.input(HV_PIN))

    def _set_relay(self, on: bool):
        if not _GPIO_AVAILABLE:
            return
        GPIO.output(RELAY_PIN, GPIO.HIGH if on else GPIO.LOW)
