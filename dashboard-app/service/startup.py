"""
service/startup.py
──────────────────
Pure startup sequence logic — no pygame, no drawing.
Tracks the interlock chain phases and TSAL blink state.
Consumed by ui/startup.py (and testable standalone).
"""

# ── Attempt to import RPi GPIO ────────────────────────────────────────────
try:
    import RPi.GPIO as GPIO

    _GPIO_AVAILABLE = True
    KEY_PIN = 17
    TSMS_PIN = 27
except ImportError:
    _GPIO_AVAILABLE = False

# ── Phases ────────────────────────────────────────────────────────────────
PHASE_LV_ON = 0
PHASE_KEY_WAIT = 1
PHASE_TSMS_WAIT = 2
PHASE_TSAL = 3
PHASE_READY = 4

# ── Timing ────────────────────────────────────────────────────────────────
TSAL_BLINK_HZ = 2.0
TSAL_BLINK_MS = int(1000 / TSAL_BLINK_HZ / 2)  # half-period
TSAL_BLINKS_REQUIRED = 6
READY_HOLD_MS = 1500


class StartupService:
    """
    Manages startup interlock state.
    Call tick(now_ms) every frame; read properties to get current state.
    """

    def __init__(self):
        self.reset()
        if _GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(KEY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(TSMS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    # ── Public inputs (set by UI on keyboard/GPIO) ─────────────────────────
    def inject_key(self):
        self._key_state = True

    def inject_tsms(self):
        self._tsms_state = True

    # ── Public read-only state ─────────────────────────────────────────────
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

    # ── tick ──────────────────────────────────────────────────────────────
    def tick(self, now_ms: int):
        """Advance state machine. Call once per frame with current ms timestamp."""
        self._poll_gpio()

        if self._phase == PHASE_LV_ON:
            self._phase = PHASE_KEY_WAIT

        elif self._phase == PHASE_KEY_WAIT:
            if self._key_state:
                print("[STARTUP] Key accepted → waiting for TSMS")
                self._phase = PHASE_TSMS_WAIT

        elif self._phase == PHASE_TSMS_WAIT:
            if self._tsms_state:
                print("[STARTUP] TSMS closed → HV ON → TSAL blinking")
                self._phase = PHASE_TSAL
                self._tsal_last = now_ms

        elif self._phase == PHASE_TSAL:
            if now_ms - self._tsal_last >= TSAL_BLINK_MS:
                self._tsal_on = not self._tsal_on
                self._tsal_last = now_ms
                if self._tsal_on:
                    self._tsal_blinks += 1
            if self._tsal_blinks >= TSAL_BLINKS_REQUIRED:
                print("[STARTUP] TSAL blink complete → READY")
                self._phase = PHASE_READY
                self._ready_at = now_ms

        elif self._phase == PHASE_READY:
            if now_ms - self._ready_at >= READY_HOLD_MS:
                self.reset()
                self._navigate_away = True

    # ── reset ─────────────────────────────────────────────────────────────
    def reset(self):
        self._phase = PHASE_LV_ON
        self._tsal_on = False
        self._tsal_last = 0
        self._tsal_blinks = 0
        self._ready_at = 0
        self._key_state = False
        self._tsms_state = False
        self._navigate_away = False

    # ── GPIO poll ─────────────────────────────────────────────────────────
    def _poll_gpio(self):
        if not _GPIO_AVAILABLE:
            return
        self._key_state = GPIO.input(KEY_PIN)
        self._tsms_state = GPIO.input(TSMS_PIN)
