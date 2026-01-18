#include <Wire.h>
#include <WiFi.h>
#include <EEPROM.h>
#include <Adafruit_AHTX0.h>
#include <Adafruit_BMP280.h>

// ===================== EEPROM =====================
#define EEPROM_SIZE 128
#define ADDR_FLAG   0
#define ADDR_SSID   1
#define ADDR_PASS   33

// ===================== SENSORES =====================
Adafruit_AHTX0 aht;
Adafruit_BMP280 bmp(0x76);

bool ahtOK = false;
bool bmpOK = false;

// ===================== UV =====================
#define UV_PIN 34
int uvIndex = 0;
String uvNivel = "";

// ===================== WIFI =====================
WiFiServer server(3333);
bool wifiOK = false;

// ===================== PROTOTIPOS =====================
void saveWiFi(String ssid, String pass);
bool loadWiFi(String &ssid, String &pass);
void startWiFiAP(String ssid, String pass);
String buildDataPacket();

// ===================== SETUP =====================
void setup() {
  Serial.begin(115200);
  Wire.begin();
  EEPROM.begin(EEPROM_SIZE);

  Serial.println("🔧 Iniciando sensores...");

  if (aht.begin()) {
    ahtOK = true;
    Serial.println("AHT20 OK");
  }

  if (bmp.begin(0x76)) {
    bmpOK = true;
    Serial.println("BMP280 OK");
  }

  pinMode(UV_PIN, INPUT);

  // 🔴 Apagar WiFi previo
  WiFi.mode(WIFI_OFF);
  delay(1000);

  // ===================== RESTAURAR WIFI =====================
  String ssid, pass;
  if (loadWiFi(ssid, pass)) {
    Serial.println("📡 Restaurando WiFi guardado...");
    startWiFiAP(ssid, pass);
  }
}

// ===================== LOOP =====================
void loop() {
  handleSerialCommands();
  handleWiFiClient();
}

// ===================== SERIAL =====================
void handleSerialCommands() {
  if (!Serial.available()) return;

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();

  // -------- CONFIGURAR WIFI --------
  if (cmd.startsWith("SET_WIFI")) {
    int p1 = cmd.indexOf(',');
    int p2 = cmd.indexOf(',', p1 + 1);

    if (p1 < 0 || p2 < 0) {
      Serial.println("ERR_WIFI");
      return;
    }

    String ssid = cmd.substring(p1 + 1, p2);
    String pass = cmd.substring(p2 + 1);

    // Apagar WiFi anterior
    WiFi.softAPdisconnect(true);
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    delay(1000);

    // Guardar en EEPROM
    saveWiFi(ssid, pass);

    // Crear nuevo AP
    startWiFiAP(ssid, pass);

    Serial.println("OK_WIFI");
    return;
  }

  // -------- PEDIR DATOS --------
  if (cmd == "DATA") {
    Serial.println(buildDataPacket());
  }
}

// ===================== WIFI CLIENT =====================
void handleWiFiClient() {
  if (!wifiOK) return;

  WiFiClient client = server.available();
  if (!client) return;

  while (client.connected()) {
    if (client.available()) {
      String cmd = client.readStringUntil('\n');
      cmd.trim();

      if (cmd == "DATA") {
        client.println(buildDataPacket());
      }
    }
  }
  client.stop();
}

// ===================== DATA PACKET =====================
String buildDataPacket() {
  int adc = analogRead(UV_PIN);
  float volt = adc * (3.3 / 4095.0);
  float mV = volt * 1000.0;

  if (mV < 50) uvIndex = 0;
  else if (mV < 227) uvIndex = 1;
  else if (mV < 318) uvIndex = 2;
  else if (mV < 408) uvIndex = 3;
  else if (mV < 503) uvIndex = 4;
  else if (mV < 606) uvIndex = 5;
  else if (mV < 696) uvIndex = 6;
  else if (mV < 795) uvIndex = 7;
  else if (mV < 881) uvIndex = 8;
  else if (mV < 976) uvIndex = 9;
  else if (mV < 1079) uvIndex = 10;
  else uvIndex = 11;

  if (uvIndex <= 2) uvNivel = "Bajo";
  else if (uvIndex <= 5) uvNivel = "Moderado";
  else if (uvIndex <= 7) uvNivel = "Alto";
  else if (uvIndex <= 10) uvNivel = "Muy Alto";
  else uvNivel = "Extremo";

  String temp = "NA", hum = "NA";
  if (ahtOK) {
    sensors_event_t h, t;
    aht.getEvent(&h, &t);
    temp = String(t.temperature, 1);
    hum = String(h.relative_humidity, 1);
  }

  String pres = "NA";
  if (bmpOK) {
    pres = String(bmp.readPressure(), 0);
  }

  return String(uvIndex) + "," + uvNivel + "," + temp + "," + hum + "," + pres;
}

// ===================== EEPROM =====================
void saveWiFi(String ssid, String pass) {
  EEPROM.write(ADDR_FLAG, 0xAA);

  for (int i = 0; i < 32; i++) {
    EEPROM.write(ADDR_SSID + i, i < ssid.length() ? ssid[i] : 0);
    EEPROM.write(ADDR_PASS + i, i < pass.length() ? pass[i] : 0);
  }

  EEPROM.commit();
}

bool loadWiFi(String &ssid, String &pass) {
  if (EEPROM.read(ADDR_FLAG) != 0xAA) return false;

  ssid = "";
  pass = "";

  for (int i = 0; i < 32; i++) {
    char c1 = EEPROM.read(ADDR_SSID + i);
    char c2 = EEPROM.read(ADDR_PASS + i);
    if (c1) ssid += c1;
    if (c2) pass += c2;
  }

  return ssid.length() > 0;
}

// ===================== WIFI AP =====================
void startWiFiAP(String ssid, String pass) {
  WiFi.mode(WIFI_AP);
  bool ok = WiFi.softAP(ssid.c_str(), pass.c_str());

  if (!ok) {
    wifiOK = false;
    Serial.println("ERR_WIFI");
    return;
  }

  server.begin();
  wifiOK = true;

  Serial.print("📡 WiFi AP activo: ");
  Serial.println(ssid);
}
