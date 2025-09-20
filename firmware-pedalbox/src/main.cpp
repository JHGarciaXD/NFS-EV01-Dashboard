// Week 1 firmware stub (no hardware needed yet).
// Week 2 will add MCP2515 + fake waveforms over CAN.
#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  static bool on = false;
  on = !on;
  digitalWrite(LED_BUILTIN, on ? HIGH : LOW);
  Serial.println(F("FS Pedalbox FW stub running..."));
  delay(500);
}
