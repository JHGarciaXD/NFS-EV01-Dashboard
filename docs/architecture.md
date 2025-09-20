# Architecture Overview (Week 1)

- **Dashboard (Pi/PC):** Python app renders UI @ 30 FPS; receives CAN; shows APPS/Brake and status banner.
- **Pedal MCU (Arduino):** Will handle sampling, filtering, plausibility, CAN publish (Week 2+).
- **Protocol:** Custom CAN with DBC. For Week 1 we use a minimal frame (`0x101 Pedal_Processed`).

```mermaid
flowchart LR
  A[Fake Sender (PC)] -- vcan0 --> D[Dashboard App (Pygame)]
  subgraph Week 2+
    M[Arduino Pedalbox] -- CAN --> D
  end
```
