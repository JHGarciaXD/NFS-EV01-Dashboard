# PC Development Setup

## Virtual CAN
Create a virtual CAN interface:
```bash
sudo ./tools/setup_vcan.sh
```
This loads `vcan`, creates `vcan0`, and brings it up. Check with:
```bash
ip link show vcan0
```

## Run the dashboard
```bash
python dashboard-app/main.py
```

## Simulate data
```bash
python tools/send_fake.py
```

## Troubleshooting
- If the window is sluggish, ensure nothing prints every frame and your GPU driver is OK.
- Use `candump vcan0` to see raw frames.
