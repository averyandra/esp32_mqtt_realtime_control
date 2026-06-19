import config as conf
import paho.mqtt.client as mqtt
import try_sender as sender
import time

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id="flip flop")
client.connect(conf.MQTT_BROKER, conf.MQTT_PORT, 60)
state = "OFF"
click = 199
for i in range(click * 2):
    state = "ON" if state == "OFF" else "OFF"
    print(f"state: {state} {i}")
    sender.send_command(client, "vorsa/control/led", state)
    time.sleep(0.4)
client.disconnect()



