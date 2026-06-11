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
        "lamp": "OFF", "led": "OFF", "fan": "OFF"
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
        
        print(f"📡 [MQTT INBOUND] Topic: {msg.topic} | Payload: {payload_str}")
        
        payload_str = payload_str.replace('nan', 'null').replace('NAN', 'null').replace('NaN', 'null')
        raw_data = json.loads(payload_str)

        if msg.topic == TOPIC_TELEMETRY:
            latest_cache["telemetry"]["12v"] = raw_data.get("12v") or raw_data.get("v12") or latest_cache["telemetry"]["12v"]
            latest_cache["telemetry"]["5v"] = raw_data.get("5v") or raw_data.get("v5") or latest_cache["telemetry"]["5v"]
            latest_cache["telemetry"]["5vsb"] = raw_data.get("5vsb") or raw_data.get("v5vsb") or latest_cache["telemetry"]["5vsb"]
            latest_cache["telemetry"]["pg"] = raw_data.get("pg") if raw_data.get("pg") is not None else raw_data.get("power_good", latest_cache["telemetry"]["pg"])
            
            # Parsing data lingkungan
            if "env" in raw_data:
                env_raw = raw_data["env"]
                latest_cache["telemetry"]["env"]["temp"] = env_raw.get("temp") or env_raw.get("temperature") or latest_cache["telemetry"]["env"]["temp"]
                latest_cache["telemetry"]["env"]["hum"] = env_raw.get("hum") or env_raw.get("humidity") or latest_cache["telemetry"]["env"]["hum"]
                latest_cache["telemetry"]["env"]["pres"] = env_raw.get("pres") or env_raw.get("pressure") or latest_cache["telemetry"]["env"]["pres"]
            else:
                latest_cache["telemetry"]["env"]["temp"] = raw_data.get("temp") or raw_data.get("temperature") or latest_cache["telemetry"]["env"]["temp"]
                latest_cache["telemetry"]["env"]["hum"] = raw_data.get("hum") or raw_data.get("humidity") or latest_cache["telemetry"]["env"]["hum"]
                latest_cache["telemetry"]["env"]["pres"] = raw_data.get("pres") or raw_data.get("pressure") or latest_cache["telemetry"]["env"]["pres"]

        elif msg.topic == TOPIC_STATUS:
            latest_cache["status"]["lamp"] = raw_data.get("lamp") or raw_data.get("lampu") or latest_cache["status"]["lamp"]
            latest_cache["status"]["led"] = raw_data.get("led") or raw_data.get("led") or latest_cache["status"]["led"]
            latest_cache["status"]["fan"] = raw_data.get("fan") or raw_data.get("fan") or latest_cache["status"]["fan"]

        save_cache_to_disk()

    except Exception as e:
        print(f"❌ [ERROR Listener]: just an error. Detail: {e}")

def main():
    print("[-] yes?...")
    save_cache_to_disk()

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
