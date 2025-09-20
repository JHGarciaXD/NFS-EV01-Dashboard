import time, math
import can

bus = can.interface.Bus(channel="vcan0", bustype="socketcan")
t0 = time.time()
counter = 0

while True:
    t = time.time() - t0
    apps = int((math.sin(2*math.pi*0.2*t)*0.5+0.5)*255)  # ~0.2 Hz sine
    tri = abs((t % 2.0) - 1.0)                            # 0..1..0 triangle
    brake = int(tri * 255)

    status = 0x00  # set nonzero to simulate a fault
    data = bytes([apps, brake, status, counter & 0x0F, 0,0,0,0])
    msg = can.Message(arbitration_id=0x101, data=data, is_extended_id=False)
    bus.send(msg)
    counter = (counter + 1) & 0x0F
    time.sleep(0.01)  # 100 Hz
