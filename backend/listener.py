import json
import os
import paho.mqtt.client as mqtt
from config import MQTT_BROKER, MQTT_PORT, TOPIC_TELEMETRY, TOPIC_STATUS, STATE_FILE

DEFAULT_STRUCTURE = {
    "telemetry": {
        "12v": 0.0, "5v": 0.0, "5vsb": 0.0, "pg": 0,
        "env": {"temp": 0.0, "hum": 0, "pres": 0.0}
    },
    "status": {
        "lamp": "OFF", "led": "OFF", "rack_led": "OFF", "fan": "OFF"
    },
    "cf": {
        "v12": 1.0, "v5": 1.0, "v5sb": 1.0
    }
}

latest_cache = DEFAULT_STRUCTURE.copy()

def save_cache_to_disk():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(latest_cache, f, indent=4)
    except Exception as e:
        print(f"[!] cant write to {STATE_FILE}: {e}")

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("[-] Listener active, listening to broker")
        client.subscribe(TOPIC_TELEMETRY)
        client.subscribe(TOPIC_STATUS)
    else:
        print(f"[!] Failed connecting listener to Broker, code: {reason_code}")

def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode('utf-8')
        print(f"[MQTT INBOUND] Topic: {msg.topic} | Payload: {payload_str}")
        
        # Guard against nan values from sensor failure
        payload_str = payload_str.replace('nan', 'null').replace('NAN', 'null').replace('NaN', 'null')
        raw_data = json.loads(payload_str)

        if msg.topic == TOPIC_TELEMETRY:
            latest_cache["telemetry"]["12v"] = raw_data.get("12v") or raw_data.get("v12") or latest_cache["telemetry"]["12v"]
            latest_cache["telemetry"]["5v"] = raw_data.get("5v") or raw_data.get("v5") or latest_cache["telemetry"]["5v"]
            latest_cache["telemetry"]["5vsb"] = raw_data.get("5vsb") or raw_data.get("v5vsb") or latest_cache["telemetry"]["5vsb"]
            latest_cache["telemetry"]["pg"] = raw_data.get("pg") if raw_data.get("pg") is not None else latest_cache["telemetry"]["pg"]
            
            if "env" in raw_data:
                env_raw = raw_data["env"]
                latest_cache["telemetry"]["env"]["temp"] = env_raw.get("temp") if env_raw.get("temp") is not None else latest_cache["telemetry"]["env"]["temp"]
                latest_cache["telemetry"]["env"]["hum"] = env_raw.get("hum") if env_raw.get("hum") is not None else latest_cache["telemetry"]["env"]["hum"]
                latest_cache["telemetry"]["env"]["pres"] = env_raw.get("pres") if env_raw.get("pres") is not None else latest_cache["telemetry"]["env"]["pres"]

        elif msg.topic == TOPIC_STATUS:
            # Convert raw ESP32 state integers (1/0) to readable UI status (ON/OFF)
            if "R1" in raw_data:
                latest_cache["status"]["lamp"] = "ON" if str(raw_data["R1"]) == "1" else "OFF"
            if "R2" in raw_data:
                latest_cache["status"]["led"] = "ON" if str(raw_data["R2"]) == "1" else "OFF"
            if "R3" in raw_data:
                latest_cache["status"]["rack_led"] = "ON" if str(raw_data["R3"]) == "1" else "OFF"
            if "R4" in raw_data:
                latest_cache["status"]["fan"] = "ON" if str(raw_data["R4"]) == "1" else "OFF"
            
            # Capture live correction factors feedback from ESP32
            if "cf" in raw_data:
                cf_raw = raw_data["cf"]
                latest_cache["cf"]["v12"] = cf_raw.get("v12", latest_cache["cf"]["v12"])
                latest_cache["cf"]["v5"] = cf_raw.get("v5", latest_cache["cf"]["v5"])
                latest_cache["cf"]["v5sb"] = cf_raw.get("v5sb", latest_cache["cf"]["v5sb"])

        save_cache_to_disk()

    except Exception as e:
        print(f"❌ [ERROR Listener]: {e}")

def main():
    print("[-] Starting MQTT Listener Service...")
    save_cache_to_disk()

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()

    except KeyboardInterrupt:
        print("\nexit....\n")

if __name__ == "__main__":
    main()