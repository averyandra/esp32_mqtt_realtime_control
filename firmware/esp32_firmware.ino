#include <WiFi.h>
#include <PubSubClient.h>
#include <U8g2lib.h>
#include <Wire.h>
#include <Adafruit_BMP280.h>
#include <Adafruit_AHTX0.h>

// Network & MQTT config
const char* ssid         = "wifi-ssid";
const char* password     = "password";
const char* mqtt_server  = "server-ip";
const int mqtt_port      = 1883; // default

// MQTT Topic
const char* topic_telemetry = "lab1/psu/1/telemetry";
const char* topic_status    = "lab1/psu/1/status";
const char* topic_control   = "lab1/control/#"; 

// --- Pin Definition (Relays) ---
#define PIN_R1 25 // main lamp
#define PIN_R2 26 // led at my desk
#define PIN_R3 27 // fan.. i guess?

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
bool pg_status = false;
float temperature = NAN, humidity = NAN, pressure = NAN;
bool ahtReady = false, bmpReady = false;

// ADC function for calculate attenuator... i guess
float readVoltage(int pin, float r1, float r2) {
  int adcVal = analogRead(pin);
  float vOut = (adcVal * 3.3) / 4095.0;
  return vOut * ((r1 + r2) / r2);
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
    if (message == "1")  digitalWrite(PIN_R1, LOW); // active low
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
  u8g2.setCursor(65, 62);
  String actState = "R1:" + String(digitalRead(PIN_R1) == LOW ? "1" : "0") +
                    " R2:" + String(digitalRead(PIN_R2) == HIGH ? "1" : "0") +
                    " R3:" + String(digitalRead(PIN_R3) == HIGH ? "1" : "0");
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
  digitalWrite(PIN_R1, LOW); // Default OFF (Active Low)

  pinMode(PIN_R2, OUTPUT);
  digitalWrite(PIN_LED_STRIP, LOW);

  pinMode(PIN_R3, OUTPUT);
  digitalWrite(PIN_R3, LOW);
  
  pinMode(PIN_PIN_PG, INPUT);
  analogReadResolution(12);

  // 5. Connect Network & MQTT Broker
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
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
    v12  = readVoltage(PIN_ADC_12V, 15100.0, 5100.0);
    v5   = readVoltage(PIN_ADC_5V, 10000.0, 15100.0);
    v5sb = readVoltage(PIN_ADC_5VSB, 10000.0, 15100.0);
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

  // Task 2: actuator status to broker (1000ms / 1s)
  if (currentMillis - lastStatusTime >= statusInterval) {
    lastStatusTime = currentMillis;

    String statusPayload = "{\"R1\":" + String(digitalRead(PIN_R1) == LOW ? "\"1\"" : "\"0\"") +
                           ",\"R2\":" + String(digitalRead(PIN_R2) == HIGH ? "\"1\"" : "\"0\"") +
                           ",\"R3\":" + String(digitalRead(PIN_R3) == HIGH ? "\"1\"" : "\"0\"") + "}";
    
    client.publish(topic_status, statusPayload.c_str());
  }
}