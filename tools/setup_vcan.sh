#!/usr/bin/env bash
set -euo pipefail
if ! lsmod | grep -q '^vcan'; then
  sudo modprobe vcan
fi
if ! ip link show vcan0 >/dev/null 2>&1; then
  sudo ip link add dev vcan0 type vcan
fi
sudo ip link set up vcan0
echo "vcan0 is up:"
ip -details link show vcan0 | sed -n '1,3p'
