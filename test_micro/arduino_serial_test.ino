void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 2000) {} // Wait for serial port to be ready (optional for Teensy)
}

void loop() {
  static int n = 0;
  Serial.print("count=");
  Serial.println(n++);
  delay(200);
}
