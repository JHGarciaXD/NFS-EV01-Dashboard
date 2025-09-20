# Plausibility Spec (stub)

> Week 2: Implement on MCU (Arduino). Dashboard only **displays** status.

Initial rules (tunable):
- **APPS agreement**: |APPS1−APPS2| ≤ 10% FS
- **APPS rate limit**: ≤ 20%FS / 10 ms
- **Brake-throttle overlap**: Brake% > 15% ⇒ APPS_cmd = 0, fault
- **Range checks**: valid window 2–98%

StatusBits map (WIP):
- bit0: APPS_AGREE
- bit1: APPS_RATE
- bit2: BRAKE_OVERLAP
- bit3: RANGE
- bit7: LATCHED
