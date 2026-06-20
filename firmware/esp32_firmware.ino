#include <WiFi.h>
#include <PubSubClient.h>
#include <U8g2lib.h>
#include <Wire.h>
#include <Adafruit_BMP280.h>
#include <Adafruit_AHTX0.h>
#include <ArduinoJson.h> // Dynamic JSON handling library
#include <ArduinoOTA.h> 

// Network & MQTT config
const char* ssid         = "wifi-ssid";
const char* password     = "password";
const char* mqtt_server  = "server-ip";
const int mqtt_port      = 1883; // default

// MQTT Topic
const char* topic_telemetry = "lab/psu/1/telemetry";
const char* topic_status    = "lab/psu/1/status";
const char* topic_control   = "lab/control/1/#"; // Scoped to PSU ID 1

// --- Pin Definition (Relays) -> control relays by digital ouptut ---
#define PIN_R1 25 // main lamp
#define PIN_R2 26 // led at my desk
#define PIN_R3 14 // led at my rack -> need correction pin value
#define PIN_R4 27 // fan.. i guess? -> need correction pin value

// Voltage meter
#define PIN_ADC_12V     32
#define PIN_ADC_5V      33
#define PIN_ADC_5VSB    34
#define PIN_PIN_PG      35 // psu status (power good) -> digital read

// --- Initialize Sensor & Display ---
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);
Adafruit_BMP280 bmp;
Adafruit_AHTX0 aht;

WiFiClient espClient;
PubSubClient client(espClient);

// --- Timing variable (Millis) ---
unsigned long lastTelemetryTime = 0;
unsigned long lastStatusTime    = 0;
const long telemetryInterval    = 500;  // 500ms for telemetry, Sensor, & OLED
const long statusInterval       = 1000; // 1s for actuator

// --- Data variables ---
float v12 = 0.0, v5 = 0.0, v5sb = 0.0;
float v12err = 1.0, v5err = 1.0, v5sberr = 1.0; // voltage measurements correction factor
bool pg_status = false;
float temperature = NAN, humidity = NAN, pressure = NAN;
bool ahtReady = false, bmpReady = false;

float readVoltage(int pin, float r1, float r2, float calibrationFactor) {
  int adcVal = analogRead(pin);
  
  // 4095.0 for ADC 12-bit ESP32
  float vOut = (adcVal * 3.3) / 4095.0; 
  float rawVoltage = vOut * ((r1 + r2) / r2);
  return rawVoltage * calibrationFactor;
}

void setup_wifi() {
  delay(10);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { 
    delay(500); 
  }
}

// mqtt callback or process incoming data 
void callback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (int i = 0; i < length; i++) { message += (char)payload[i]; }
  
  String strTopic = String(topic);
  
  if (strTopic.endsWith("R1")) {
    if (message == "1")  digitalWrite(PIN_R1, LOW); // active low for relay that on if signal input is low
    if (message == "0") digitalWrite(PIN_R1, HIGH);
  } 
  else if (strTopic.endsWith("R2")) {
    if (message == "1")  digitalWrite(PIN_R2, HIGH);
    if (message == "0") digitalWrite(PIN_R2, LOW);
  } 
  else if (strTopic.endsWith("R3")) {
    if (message == "1")  digitalWrite(PIN_R3, HIGH);
    if (message == "0") digitalWrite(PIN_R3, LOW);
  }
  else if (strTopic.endsWith("R4")) {
    if (message == "1")  digitalWrite(PIN_R4, HIGH);
    if (message == "0") digitalWrite(PIN_R4, LOW);
  }
  // Parsing Incoming JSON Correction Factors
  else if (strTopic.endsWith("CF")) {
    JsonDocument doc; 
    DeserializationError error = deserializeJson(doc, message);

    if (!error) {
      if (doc.containsKey("v12"))   v12err   = doc["v12"];
      if (doc.containsKey("v5"))    v5err    = doc["v5"];
      if (doc.containsKey("v5sb"))  v5sberr  = doc["v5sb"];
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP32_Lab_Controller")) {
      client.subscribe(topic_control);
    } else {
      delay(2000); 
    }
  }
}

void updateDisplay() {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x10_tf);
  
  // Header (yellow)
  u8g2.drawStr(0, 10, "LAB MONITOR");
  u8g2.drawHLine(0, 12, 128);
  
  // row 1: Main voltage (blue)
  u8g2.setCursor(0, 24); 
  u8g2.print("12V:" + String(v12, 1) + "V 5V:" + String(v5, 1) + "V SB:" + String(v5sb, 1) + "V");
  
  // row 2: environment data (temp & humidity)
  u8g2.setCursor(0, 36);
  if (ahtReady) {
    u8g2.print("Temp:" + String(temperature, 1) + "C Hum:" + String(humidity, 0) + "%");
  } else {
    u8g2.print("AHT20: ERROR");
  }

  // row 3: pressure & power good psu
  u8g2.setCursor(0, 48);
  if (bmpReady) {
    u8g2.print("Pres:" + String(pressure / 100.0, 1) + "hPa");
  } else {
    u8g2.print("BMP280: ERROR");
  }
  
  // row 4: pg status & actuator status
  u8g2.setCursor(0, 62);
  u8g2.print("PG:" + String(pg_status ? "OK" : "FAIL"));
  
  // Status singkat aktuator di pojok kanan bawah
  u8g2.setCursor(55, 62);
  String actState = "R1:" + String(digitalRead(PIN_R1) == LOW ? "1" : "0") +
                    " R2:" + String(digitalRead(PIN_R2) == HIGH ? "1" : "0") +
                    " R3:" + String(digitalRead(PIN_R3) == HIGH ? "1" : "0") +
                    " R4:" + String(digitalRead(PIN_R4) == HIGH ? "1" : "0");
  u8g2.print(actState);
  
  u8g2.sendBuffer();
}

void setup() {
  // 1. Init I2C Bus Hardware 
  Wire.begin();

  // 2. Init OLED & show status booting
  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x10_tf);
  u8g2.drawStr(0, 12, "LAB PERIPHERAL");
  u8g2.drawStr(0, 32, "Initializing Sensors...");
  u8g2.sendBuffer();

  // 3. Init I2C Sensor
  ahtReady = aht.begin();
  bmpReady = bmp.begin(); // default address BMP280 library Adafruit is 0x77

  u8g2.clearBuffer();
  u8g2.drawStr(0, 12, "LAB PERIPHERAL");
  u8g2.drawStr(0, 32, "Connecting WiFi...");
  u8g2.sendBuffer();

  // 4. Setup Pin actuator mode
  pinMode(PIN_R1, OUTPUT);
  digitalWrite(PIN_R1, LOW); // Default OFF (Active Low), keep this, i want this to default ON

  pinMode(PIN_R2, OUTPUT);
  digitalWrite(PIN_R2, LOW);

  pinMode(PIN_R3, OUTPUT);
  digitalWrite(PIN_R3, LOW);

  pinMode(PIN_R4, OUTPUT);
  digitalWrite(PIN_R4, LOW);
  
  pinMode(PIN_PIN_PG, INPUT);
  analogReadResolution(12);

  // 5. Connect Network & MQTT Broker
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);

  ArduinoOTA.setHostname("ESP32_Lab_PSU_1"); // The name that will appear in the Arduino IDE
  ArduinoOTA.setPassword("password");     // Optional: Give a password so that not just anyone can flash it.
  
  ArduinoOTA.onStart([]() {
    u8g2.clearBuffer();
    u8g2.drawStr(0, 12, "OTA UPDATE");
    u8g2.drawStr(0, 32, "Receiving firmware...");
    u8g2.sendBuffer();
  });
  
  ArduinoOTA.onEnd([]() {
    u8g2.clearBuffer();
    u8g2.drawStr(0, 12, "OTA UPDATE");
    u8g2.drawStr(0, 32, "Update Success!");
    u8g2.drawStr(0, 48, "Rebooting...");
    u8g2.sendBuffer();
  });

  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    u8g2.clearBuffer();
    u8g2.drawStr(0, 12, "OTA UPDATE");
    u8g2.setCursor(0, 32);
    u8g2.print("Progress: " + String(progress / (total / 100)) + "%");
    u8g2.sendBuffer();
  });

  ArduinoOTA.onError([](ota_error_t error) {
    u8g2.clearBuffer();
    u8g2.drawStr(0, 12, "OTA ERROR");
    u8g2.sendBuffer();
  });

  ArduinoOTA.begin();

}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long currentMillis = millis();

  // Task 1: read sensor, Update Screen & Telemetry MQTT (500ms)
  if (currentMillis - lastTelemetryTime >= telemetryInterval) {
    lastTelemetryTime = currentMillis;

    // read PSU electrical parameter
    v12  = readVoltage(PIN_ADC_12V, 15100.0, 5100.0, v12err);
    v5   = readVoltage(PIN_ADC_5V, 10000.0, 15100.0, v5err);
    v5sb = readVoltage(PIN_ADC_5VSB, 10000.0, 15100.0, v5sberr);
    pg_status = digitalRead(PIN_PIN_PG);

    // read environment data if sensors are ok
    if (ahtReady) {
      sensors_event_t humidity_event, temp_event;
      aht.getEvent(&humidity_event, &temp_event);
      temperature = temp_event.temperature;
      humidity = humidity_event.relative_humidity;
    }
    if (bmpReady) {
      pressure = bmp.readPressure();
    }

    // JSON payload, telemetry publish
    String payload = "{\"12v\":" + String(v12, 2) + 
                     ",\"5v\":" + String(v5, 2) + 
                     ",\"5vsb\":" + String(v5sb, 2) + 
                     ",\"pg\":" + String(pg_status) +
                     ",\"env\":{\"temp\":" + String(temperature, 2) +
                     ",\"hum\":" + String(humidity, 2) +
                     ",\"pres\":" + String(pressure / 100.0, 2) + "}}";
                     
    client.publish(topic_telemetry, payload.c_str());
    updateDisplay(); 
  }

  // Task 2: actuator status and correction factor to broker (1000ms / 1s)
  if (currentMillis - lastStatusTime >= statusInterval) {
    lastStatusTime = currentMillis;

    // Combined JSON string including Relays state and live Active Correction Factors (CF)
    String statusPayload = "{\"R1\":" + String(digitalRead(PIN_R1) == LOW ? "1" : "0") +
                           ",\"R2\":" + String(digitalRead(PIN_R2) == HIGH ? "1" : "0") +
                           ",\"R3\":" + String(digitalRead(PIN_R3) == HIGH ? "1" : "0") +
                           ",\"R4\":" + String(digitalRead(PIN_R4) == HIGH ? "1" : "0") + 
                           ",\"cf\":{\"v12\":" + String(v12err, 4) +
                           ",\"v5\":" + String(v5err, 4) +
                           ",\"v5sb\":" + String(v5sberr, 4) + "}}";
    
    client.publish(topic_status, statusPayload.c_str());
  }
}