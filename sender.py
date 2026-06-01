# sender.py
import paho.mqtt.client as mqtt
from config import MQTT_BROKER, MQTT_PORT, TOPIC_CONTROL_PREFIX

def send_command(device: str, state: str):
    """
    Mengirim perintah kontrol ke ESP32 via Broker Armbian.
    device: 'lampu', 'led', atau 'fan'
    state: 'ON' atau 'OFF'
    """
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        topic = f"{TOPIC_CONTROL_PREFIX}{device}"
        # Kirim dengan flag retain agar state tersimpan di broker
        client.publish(topic, state, retain=True)
        client.disconnect()
        return {"status": "success", "topic": topic, "message": state}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# Contoh penggunaan mandiri untuk testing:
if __name__ == "__main__":
    # Tes nyalakan lampu lewat terminal
    print(send_command("lampu", "ON"))
