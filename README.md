# FS Dashboard — Setup & Run Guide

Two environments are supported:

| Environment | CAN interface | Display |
|---|---|---|
| **Linux PC** (dev) | `vcan0` (virtual) | any desktop |
| **Raspberry Pi** (car) | `can0` via MCP2515 SPI hat | HDMI / DSI screen |

Conda is used for the Python environment on both — it works identically on any
Linux distro (Arch, Fedora, Ubuntu, Debian, etc.) without touching system Python.

---

## Repository layout

```
dashboard/
├── main.py
├── can_rx.py
├── requirements.txt
├── ui/
│   ├── theme.py
│   ├── widgets.py
│   ├── dashboard.py
│   └── menu.py
└── assets/
    └── fonts/
        └── DSEG14Classic-Bold.ttf
```

---

## 0 — Install Conda (once, both machines)

If you don't have Conda yet, install **Miniforge** (recommended — free, no licence issues):

```bash
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh -b -p "$HOME/miniforge3"
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda init bash        # or zsh / fish — restart terminal after this
```

On the Pi (ARM64) use the ARM installer instead:

```bash
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
bash Miniforge3-Linux-aarch64.sh -b -p "$HOME/miniforge3"
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda init bash
```

---

## 1 — Create the Conda environment (once, both machines)

```bash
conda create -n fsdash python=3.11 -y
conda activate fsdash
pip install -r requirements.txt
```

`requirements.txt` contains all Python dependencies:

```
python-can>=4.3
pygame>=2.5
```

To activate the environment in future sessions:

```bash
conda activate fsdash
```

---

## A — Linux PC (virtual CAN, development)

### A1. Install can-utils (one-time, distro-specific)

**Debian / Ubuntu / Raspberry Pi OS:**
```bash
sudo apt install -y can-utils
```

**Fedora / RHEL:**
```bash
sudo dnf install -y can-utils
```

**Arch:**
```bash
sudo pacman -S can-utils
```

### A2. Bring up the virtual CAN interface

Run once per boot:

```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set vcan0 up
```

Verify:

```bash
ip link show vcan0
# should show: vcan0: <NOARP,UP,LOWER_UP> ...
```

### A3. Run the dashboard

```bash
# Terminal A — dashboard
conda activate fsdash
python main.py
```

### A4. Send fake CAN frames

```bash
# Terminal B — fake sender
conda activate fsdash
python tools/send_fake.py
```

You should see the APPS/Brake bars moving and the banner showing **OK**.

---

## B — Raspberry Pi (MCP2515 SPI hat, real CAN)

### B1. Wire the JOY-IT MCP2515 module

| MCP2515 pin | Pi GPIO (BCM) | Pi physical pin |
|---|---|---|
| VCC | 3.3 V | 1 |
| GND | GND | 6 |
| CS | GPIO 8 (CE0) | 24 |
| SCK | GPIO 11 (SCLK) | 23 |
| SI (MOSI) | GPIO 10 (MOSI) | 19 |
| SO (MISO) | GPIO 9 (MISO) | 21 |
| INT | GPIO 25 | 22 |

> If your module has a 3.3 V / 5 V jumper, set it to **3.3 V**.

### B2. Enable SPI and the MCP2515 overlay

```bash
sudo nano /boot/firmware/config.txt
# On older Raspberry Pi OS (Bullseye) use: /boot/config.txt
```

Add at the bottom:

```ini
# SPI bus
dtparam=spi=on

# MCP2515 on SPI0 CE0 — 8 MHz oscillator, INT on GPIO 25
dtoverlay=mcp2515-can0,oscillator=8000000,interrupt=25
dtoverlay=spi-bcm2835
```

> **Oscillator frequency:** the JOY-IT module usually has an **8 MHz** crystal
> (`8.000` printed on the silver can on the PCB). If yours says `16.000`,
> change `oscillator=8000000` → `oscillator=16000000`.

Reboot:

```bash
sudo reboot
```

### B3. Bring up the CAN interface

Once after each reboot:

```bash
sudo ip link set can0 up type can bitrate 500000
```

Verify:

```bash
ip link show can0
candump can0    # shows live frames if the bus is active
```

To make it persistent, create a systemd-networkd unit:

```bash
sudo nano /etc/systemd/network/80-can0.network
```

```ini
[Match]
Name=can0

[CAN]
BitRate=500000
```

```bash
sudo systemctl enable --now systemd-networkd
```

### B4. Install can-utils on the Pi

```bash
sudo apt install -y can-utils
```

### B5. Set the CAN channel

Edit `can_rx.py` line 12:

```python
# PC (virtual)
BUS_CHANNEL = "vcan0"

# Pi (real hardware) ← change to this
BUS_CHANNEL = "can0"
```

### B6. Run the dashboard

```bash
conda activate fsdash
python main.py
```

#### Auto-start on boot (systemd service)

```bash
sudo nano /etc/systemd/system/fsdash.service
```

```ini
[Unit]
Description=FS Dashboard
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/dashboard
Environment=DISPLAY=:0
Environment=PATH=/home/pi/miniforge3/envs/fsdash/bin:/usr/bin:/bin
ExecStartPre=/sbin/ip link set can0 up type can bitrate 500000
ExecStart=/home/pi/miniforge3/envs/fsdash/bin/python main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now fsdash.service
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No module named 'can'` | `conda activate fsdash` then `pip install -r requirements.txt` |
| `No module named 'pygame'` | same as above |
| `vcan0` not found | `sudo modprobe vcan` first |
| `can0` missing after reboot | check `/boot/firmware/config.txt`; run `dmesg \| grep mcp251` |
| `mcp251x spi0.0: MCP251x failed` in dmesg | wrong oscillator — check crystal value on PCB |
| No window on Pi desktop | ensure `DISPLAY=:0` is set; a desktop session must be active |
| `OSError: [Errno 19] No such device` | `can0` is not up — run `sudo ip link set can0 up type can bitrate 500000` |
| Conda not found after install | `source ~/miniforge3/etc/profile.d/conda.sh` or restart terminal |