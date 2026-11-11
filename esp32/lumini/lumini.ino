#include <Arduino.h>

const int LED_R = 27;
const int LED_Y = 26;
const int LED_G = 25;

char cmdBuffer[16];
uint8_t bufIdx = 0;

void setLeds(char state) {
  digitalWrite(LED_R, state == 'R' ? HIGH : LOW);
  digitalWrite(LED_Y, state == 'Y' ? HIGH : LOW);
  digitalWrite(LED_G, state == 'G' ? HIGH : LOW);
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(10);

  pinMode(LED_R, OUTPUT);
  pinMode(LED_Y, OUTPUT);
  pinMode(LED_G, OUTPUT);

  digitalWrite(LED_R, HIGH);
  digitalWrite(LED_Y, HIGH);
  digitalWrite(LED_G, HIGH);
  delay(1000);

  setLeds('R');
  Serial.println("ESP32 pregatit pentru PageQ.");
}

void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      cmdBuffer[bufIdx] = '\0';
      if (bufIdx >= 5 && strncmp(cmdBuffer, "CLS:", 4) == 0) {
        char st = cmdBuffer[4];
        if (st == 'R' || st == 'Y' || st == 'G') {
          setLeds(st);
        }
      }
      bufIdx = 0;
    } else if (bufIdx < sizeof(cmdBuffer) - 1) {
      cmdBuffer[bufIdx++] = c;
    } else {
      //buffer plin fara newline, resetam ca sa nu blocam
      bufIdx = 0;
    }
  }
}