# import config as conf
# import paho.mqtt.client as mqtt
# from devices import device_list

# devices = ["r1"]

# def send_command(client, topic, state, retain: bool = False):
#     try:
#         client.publish(topic, state, retain=retain)
#         return {"status": "success", "topic": topic, "message": state}
#     except Exception as e:
#         return {"status": "error", "detail": str(e)}

# def send_multiple_command(param: dict):
#     # try:
#     #     client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
#     #     client.connect(conf.MQTT_BROKER, conf.MQTT_PORT, 60)
#     #     topic =f"{conf.TOPIC_CONTROL_PREFIX}{device}"
#     #     client.publish(param, retain=True)
#     #     client.disconnect()
#     #     return {"status": "success", "topic": topic, "message": state}
#     # except Exception as e:
#     #     return {"status": "error", "detail": str(e)}
#     pass

# def main():

#     client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        
#     try:
#         client.connect(conf.MQTT_BROKER, conf.MQTT_PORT, 60)

#         mode = int(input("[1] single or [2] multiple command :> "))
#         if mode == 1:
#             device = input("select device :> ")
#             topic = f"{conf.TOPIC_CONTROL_PREFIX}{device}"
#             state = input("select state : ON / OFF :> ")
#             print(send_command(client, topic, state, True))
#             client.disconnect()
#         elif mode == 2:
#             print(device_list[0])
#             # for i in device_list:
#             #     print(device_list[i])
#         else:
#             print("input must be [1] or [2]")
#     except ValueError:
#         print("input must be a number")

# if __name__ == "__main__":
#     main()

import json
import paho.mqtt.client as mqtt
from config import MQTT_BROKER, MQTT_PORT, TOPIC_CONTROL_PREFIX
from devices import DEVICE_MAP, device_list

def send_command(device: str, state: str or dict):
    """
    Sends command controls or configurations to ESP32 via MQTT Broker.
    device: 'lamp', 'led', 'rack_led', 'fan', 'calibrator', 'all'
    state: 'ON'/'OFF' for actuators, or dict data for 'calibrator'/'all'
    """
    if device not in DEVICE_MAP:
        return {"status": "error", "detail": f"Unknown device token: {device}"}

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        topic = f"{TOPIC_CONTROL_PREFIX}{DEVICE_MAP[device]}"
        
        # Process Payload dynamically depending on targets
        if device == "calibrator" or device == "all":
            # Direct stringify for dictionary payloads (CF and bulk controls)
            payload = json.dumps(state)
        else:
            # Map 'ON' to '1' and 'OFF' to '0' for single binary logic
            payload = "1" if state == "ON" else "0"

        client.publish(topic, payload, retain=True)
        client.disconnect()
        return {"status": "success", "topic": topic, "message": payload}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

def main():
    print("=== MQTT SENDER DEBUGGING TOOL ===")
    print(f"Available Devices: {device_list}")
    print("---------------------------------")
    
    try:
        mode = int(input("[1] Single Command or [2] Multiple Commands (Bulk JSON) :> "))
        
        if mode == 1:
            device = input("Select device (e.g., lamp/led/fan/calibrator) :> ").strip()
            
            if device == "calibrator":
                print("Enter correction factors (JSON format required, e.g., {'v12': 1.02})")
                cf_input = input("JSON Data :> ").strip()
                try:
                    state = json.loads(cf_input.replace("'", '"'))
                except json.JSONDecodeError:
                    print("❌ Invalid JSON format!")
                    return
            else:
                state = input("Select state (ON / OFF) :> ").strip().upper()
                if state not in ["ON", "OFF"]:
                    print("❌ State must be ON or OFF!")
                    return
            
            print("\nSending command...")
            print(send_command(device, state))

        elif mode == 2:
            print("\n[!] Setting states individually for all devices into a single JSON payload")
            bulk_payload = {}
            
            # Loop through each target item and ask user for inputs
            for dev in device_list:
                if dev not in ["calibrator", "all"]:
                    state = input(f"Set state for '{dev}' (ON / OFF) :> ").strip().upper()
                    if state not in ["ON", "OFF"]:
                        print("❌ Invalid input! Defaulting to OFF.")
                        state = "OFF"
                    
                    # Convert straight to ESP32 binary logic keys ("R1", "R2", etc.)
                    mqtt_key = DEVICE_MAP[dev]
                    bulk_payload[mqtt_key] = 1 if state == "ON" else 0
            
            print(f"\nConstructed Payload: {bulk_payload}")
            print("Sending bulk command to /all...")
            print(send_command("all", bulk_payload))
            
        else:
            print("❌ Input must be [1] or [2]")
            
    except ValueError:
        print("❌ Input must be a valid number!")
    except Exception as e:
        print(f"❌ Debugger Error: {e}")

if __name__ == "__main__":
    main()