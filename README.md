# FS Dashboard — Week 1 Scaffold

This is the **Week 1** starter repo for the Formula Student Dashboard project.
It lets you develop & test the dashboard **on your Linux PC** using a **virtual CAN (vcan0)**,
plus ships a minimal **MkDocs** documentation site.

## What’s included (Week 1 scope)
- **dashboard-app/** — Python + Pygame skeleton (30 FPS loop) reading CAN from `vcan0`.
- **tools/** — CAN fake sender to simulate pedal data; helper to set up `vcan0`.
- **dbc/** — Placeholder DBC (`pedal_v0_1.dbc`) for message IDs.
- **docs/** + `mkdocs.yml` — MkDocs site skeleton.
- **firmware-pedalbox/** — Arduino/PlatformIO project *stub* (Week 2).
- **.github/workflows/** — CI placeholders (lint/build stubs).

> Logging is intentionally de-emphasized. We’ll focus on MCU plausibility, CAN reliability,
> UI @ 30 FPS, diagnostics/calibration, and daylight readability.

---

## Quick start (Linux PC, no hardware)

### 0) (Optional) Conda env
```bash
conda create -n fsdash python=3.11
conda activate fsdash
pip install -r requirements.txt
```

Or use venv:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 1) Bring up a virtual CAN interface
```bash
sudo ./tools/setup_vcan.sh
```

### 2) Run the dashboard (Terminal A)
```bash
python dashboard-app/main.py
```

### 3) Send fake CAN frames (Terminal B)
```bash
python tools/send_fake.py
```

You should see APPS/Brake bars moving at ~30 FPS and the status banner showing **OK**.

---

## Next weeks
- **Week 2:** MCU filters + plausibility on Arduino; real CAN @ 100 Hz.
- **Week 3:** Diagnostics + calibration (engineering mode) — on-demand CAN service.
- **Week 4:** Daylight UI polish + stability + HIL bench.
