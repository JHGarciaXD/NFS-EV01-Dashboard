LV_PIN = 17
HV_PIN = 27
RELAY_RED_PIN = 22  # red blinking relay
RELAY_GREEN_PIN = 23  # green steady relay

TSAL_BLINK_HZ = 3.0
TSAL_BLINK_MS = int(1000 / TSAL_BLINK_HZ / 2)

try:
    import RPi.GPIO as GPIO

    _GPIO_AVAILABLE = True
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LV_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(HV_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(RELAY_RED_PIN, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(RELAY_GREEN_PIN, GPIO.OUT, initial=GPIO.HIGH)
except ImportError:
    _GPIO_AVAILABLE = False


class TSALService:
    def __init__(self):
        self._lv_on = False
        self._hv_on = False
        self._blink_on = False
        self._last_ms = 0

    def inject_lv(self):
        self._lv_on = True

    def inject_lv_off(self):
        self._lv_on = False
        self._hv_on = False

    def inject_hv(self):
        self._hv_on = True

    def inject_hv_off(self):
        self._hv_on = False

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

    def tick(self, now_ms: int):
        self._poll_gpio()
        if self._hv_on:
            # red blinking, green off
            self._set_green(False)
            if now_ms - self._last_ms >= TSAL_BLINK_MS:
                self._blink_on = not self._blink_on
                self._last_ms = now_ms
                self._set_red(self._blink_on)
        elif self._lv_on:
            # green steady, red off
            self._set_red(False)
            self._blink_on = False
            self._set_green(True)
        else:
            # both off
            self._set_red(False)
            self._set_green(False)
            self._blink_on = False

    def cleanup(self):
        if _GPIO_AVAILABLE:
            self._set_red(False)
            self._set_green(False)
            GPIO.cleanup()

    def _poll_gpio(self):
        if not _GPIO_AVAILABLE:
            return
        self._lv_on = bool(GPIO.input(LV_PIN))
        self._hv_on = bool(GPIO.input(HV_PIN))

    def _set_red(self, on: bool):
        if not _GPIO_AVAILABLE:
            return
        GPIO.output(RELAY_RED_PIN, GPIO.LOW if on else GPIO.HIGH)

    def _set_green(self, on: bool):
        if not _GPIO_AVAILABLE:
            return
        GPIO.output(RELAY_GREEN_PIN, GPIO.LOW if on else GPIO.HIGH)
