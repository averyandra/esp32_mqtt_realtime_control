import paho.mqtt.client as mqtt

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="test client"
)

def on_message(client, userdata, msg):
    print(msg.topic)
    print(msg.payload.decode())

def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"{client}disconnected")

def on_connect(client, userdata, flags, reason_code, properties):
    print("connected")
    client.subscribe("vorsa/psu/telemetry")
    

def main():
    try:
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        client.on_connect = on_connect

        client.connect("10.0.0.1", 1883, 60)
        client.loop_forever()

        
    
    except KeyboardInterrupt:
        client.disconnect()


if __name__ == "__main__":
    main()