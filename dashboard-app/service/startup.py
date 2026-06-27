"""
service/startup.py
------------------
Pure startup sequence logic — no pygame, no drawing.
Consumed by ui/startup.py.
"""

try:
    import RPi.GPIO as GPIO

    _GPIO_AVAILABLE = True
    KEY_PIN = 17
    TSMS_PIN = 27
except ImportError:
    _GPIO_AVAILABLE = False

# -- Phases -----------------------------------------------------------------
PHASE_LV_ON = 0
PHASE_KEY_WAIT = 1
PHASE_TSMS_WAIT = 2
PHASE_TSAL = 3
PHASE_READY = 4

# -- Timing -----------------------------------------------------------------
TSAL_BLINK_HZ = 2.0
TSAL_BLINK_MS = int(1000 / TSAL_BLINK_HZ / 2)
TSAL_BLINKS_REQUIRED = 6
READY_HOLD_MS = 1500


class StartupService:
    def __init__(self):
        self.reset()
        if _GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(KEY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(TSMS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    def inject_key(self):
        self._key_state = True

    def inject_tsms(self):
        self._tsms_state = True

    @property
    def phase(self) -> int:
        return self._phase

    @property
    def tsal_on(self) -> bool:
        return self._tsal_on

    @property
    def tsal_blinks(self) -> int:
        return self._tsal_blinks

    @property
    def wants_dashboard(self) -> bool:
        val = self._navigate_away
        if val:
            self._navigate_away = False
        return val

    def tick(self, now_ms: int):
        self._poll_gpio()

        if self._phase == PHASE_LV_ON:
            self._phase = PHASE_KEY_WAIT

        elif self._phase == PHASE_KEY_WAIT:
            if self._key_state:
                print("[STARTUP] Key accepted -> waiting for TSMS")
                self._phase = PHASE_TSMS_WAIT

        elif self._phase == PHASE_TSMS_WAIT:
            if self._tsms_state:
                print("[STARTUP] TSMS closed -> HV ON -> TSAL blinking")
                self._phase = PHASE_TSAL
                self._tsal_last = now_ms

        elif self._phase == PHASE_TSAL:
            if now_ms - self._tsal_last >= TSAL_BLINK_MS:
                self._tsal_on = not self._tsal_on
                self._tsal_last = now_ms
                if self._tsal_on:
                    self._tsal_blinks += 1
            if self._tsal_blinks >= TSAL_BLINKS_REQUIRED:
                print("[STARTUP] TSAL blink complete -> READY")
                self._phase = PHASE_READY
                self._ready_at = now_ms

        elif self._phase == PHASE_READY:
            if now_ms - self._ready_at >= READY_HOLD_MS:
                self.reset()
                self._navigate_away = True

    def reset(self):
        self._phase = PHASE_LV_ON
        self._tsal_on = False
        self._tsal_last = 0
        self._tsal_blinks = 0
        self._ready_at = 0
        self._key_state = False
        self._tsms_state = False
        self._navigate_away = False

    def _poll_gpio(self):
        if not _GPIO_AVAILABLE:
            return
        self._key_state = bool(GPIO.input(KEY_PIN))
        self._tsms_state = bool(GPIO.input(TSMS_PIN))
