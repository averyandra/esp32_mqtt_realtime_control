import config as conf
import paho.mqtt.client as mqtt
from devices import device_list

devices = ["r1"]

def send_command(client, topic, state, retain: bool = False):
    try:
        client.publish(topic, state, retain=retain)
        return {"status": "success", "topic": topic, "message": state}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

def send_multiple_command(param: dict):
    # try:
    #     client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    #     client.connect(conf.MQTT_BROKER, conf.MQTT_PORT, 60)
    #     topic =f"{conf.TOPIC_CONTROL_PREFIX}{device}"
    #     client.publish(param, retain=True)
    #     client.disconnect()
    #     return {"status": "success", "topic": topic, "message": state}
    # except Exception as e:
    #     return {"status": "error", "detail": str(e)}
    pass

def main():
    try:
        mode = int(input("[1] single or [2] multiple command :> "))
        if mode == 1:
            device = input("select device :> ")
            state = input("select state : ON / OFF :> ")
            print(send_command(device, state))
        if mode == 2:
            print(device_list[0])
            # for i in device_list:
            #     print(device_list[i])
        else:
            print("input must be [1] or [2]")
    except ValueError:
        print("input must be a number")

if __name__ == "__main__":
    main()