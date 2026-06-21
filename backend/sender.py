import paho.mqtt.client as mqtt
from config import MQTT_BROKER, MQTT_PORT, TOPIC_CONTROL_PREFIX

def send_command(device: str, state: str):
    """
    send command control to esp32 via broker server.
    device: 'r1', 'r2', or 'r3'
    state: 'ON' or 'OFF'
    """
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        topic = f"{TOPIC_CONTROL_PREFIX}{device}"
        client.publish(topic, state, retain=True)
        client.disconnect()
        return {"status": "success", "topic": topic, "message": state}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

if __name__ == "__main__":
    device = input("device: ")
    state = input("state: ")
    print(send_command(device, state))
