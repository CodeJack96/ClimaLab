#include <Wire.h>
#include <Adafruit_AHTX0.h>
#include <Adafruit_BMP280.h>

#define UV_PIN 34

Adafruit_AHTX0 aht;
Adafruit_BMP280 bmp(0x76);

bool ahtOK = false;
bool bmpOK = false;

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);

  if (aht.begin()) ahtOK = true;
  if (bmp.begin()) bmpOK = true;

  if (bmpOK) {
    bmp.setSampling(
      Adafruit_BMP280::MODE_NORMAL,
      Adafruit_BMP280::SAMPLING_X2,
      Adafruit_BMP280::SAMPLING_X16,
      Adafruit_BMP280::FILTER_X16,
      Adafruit_BMP280::STANDBY_MS_500
    );
  }

  delay(2000);
}

void loop() {

  // ---- AHT20 ----
  String tempAHT = "NA";
  String hum = "NA";

  if (ahtOK) {
    sensors_event_t h, t;
    aht.getEvent(&h, &t);
    tempAHT = String(t.temperature, 1);
    hum = String(h.relative_humidity, 1);
  }

  // ---- BMP280 ----
  String presion = "NA";
  if (bmpOK) presion = String(bmp.readPressure(), 0);

  // ---- UV ----
  int adc = analogRead(UV_PIN);
  float mv = (adc * 3.3 / 4095.0) * 1000.0;

  int uv;
  if (mv < 50) uv = 0;
  else if (mv < 227) uv = 1;
  else if (mv < 318) uv = 2;
  else if (mv < 408) uv = 3;
  else if (mv < 503) uv = 4;
  else if (mv < 606) uv = 5;
  else if (mv < 696) uv = 6;
  else if (mv < 795) uv = 7;
  else if (mv < 881) uv = 8;
  else if (mv < 976) uv = 9;
  else if (mv < 1079) uv = 10;
  else uv = 11;

  String nivel;
  if (uv <= 2) nivel = "Bajo";
  else if (uv <= 5) nivel = "Moderado";
  else if (uv <= 7) nivel = "Alto";
  else if (uv <= 10) nivel = "Muy Alto";
  else nivel = "Extremo";

  Serial.print(uv);
  Serial.print(",");
  Serial.print(nivel);
  Serial.print(",");
  Serial.print(tempAHT);
  Serial.print(",");
  Serial.print(hum);
  Serial.print(",");
  Serial.println(presion);

  delay(1000);  // la ESP32 envía cada 1 s
}
