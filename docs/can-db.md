# CAN & DBC (Week 1 placeholder)

## Message IDs
- **0x101 `Pedal_Processed` (8 bytes, 100 Hz)**  
  - byte0: APPS_pct (0..255 → 0..100 %)  
  - byte1: Brake_pct (0..255 → 0..100 %)  
  - byte2: StatusBits (bitfield)  
  - byte3: Counter (lower 4 bits, 0..15)  
  - byte4..7: reserved

A proper `.dbc` will evolve over Week 2–3.
