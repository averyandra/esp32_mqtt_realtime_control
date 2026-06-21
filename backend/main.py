import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import paho.mqtt.client as mqtt

from config import MQTT_BROKER, MQTT_PORT, TOPIC_TELEMETRY, TOPIC_STATUS
from devices import DEVICE_MAP
import sender

app = FastAPI(title="LAB PSU Controller & Monitor Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory state shared across MQTT thread and FastAPI async loop
SHARED_STATE = {
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

class ControlRequest(BaseModel):
    device: str  
    state: str   

class CalibrationRequest(BaseModel):
    v12: float = None
    v5: float = None
    v5sb: float = None

def on_mqtt_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("[-] MQTT Background Listener active and connected")
        client.subscribe(TOPIC_TELEMETRY)
        client.subscribe(TOPIC_STATUS)
    else:
        print(f"[!] MQTT Connection failed with code: {reason_code}")

def on_mqtt_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode('utf-8')
        payload_str = payload_str.replace('nan', 'null').replace('NAN', 'null').replace('NaN', 'null')
        raw_data = json.loads(payload_str)

        if msg.topic == TOPIC_TELEMETRY:
            SHARED_STATE["telemetry"]["12v"] = raw_data.get("12v") or raw_data.get("v12") or SHARED_STATE["telemetry"]["12v"]
            SHARED_STATE["telemetry"]["5v"] = raw_data.get("5v") or raw_data.get("v5") or SHARED_STATE["telemetry"]["5v"]
            SHARED_STATE["telemetry"]["5vsb"] = raw_data.get("5vsb") or raw_data.get("v5vsb") or SHARED_STATE["telemetry"]["5vsb"]
            SHARED_STATE["telemetry"]["pg"] = raw_data.get("pg") if raw_data.get("pg") is not None else SHARED_STATE["telemetry"]["pg"]
            
            if "env" in raw_data:
                env_raw = raw_data["env"]
                SHARED_STATE["telemetry"]["env"]["temp"] = env_raw.get("temp") if env_raw.get("temp") is not None else SHARED_STATE["telemetry"]["env"]["temp"]
                SHARED_STATE["telemetry"]["env"]["hum"] = env_raw.get("hum") if env_raw.get("hum") is not None else SHARED_STATE["telemetry"]["env"]["hum"]
                SHARED_STATE["telemetry"]["env"]["pres"] = env_raw.get("pres") if env_raw.get("pres") is not None else SHARED_STATE["telemetry"]["env"]["pres"]

        elif msg.topic == TOPIC_STATUS:
            if "R1" in raw_data:
                SHARED_STATE["status"]["lamp"] = "ON" if str(raw_data["R1"]) == "1" else "OFF"
            if "R2" in raw_data:
                SHARED_STATE["status"]["led"] = "ON" if str(raw_data["R2"]) == "1" else "OFF"
            if "R3" in raw_data:
                SHARED_STATE["status"]["rack_led"] = "ON" if str(raw_data["R3"]) == "1" else "OFF"
            if "R4" in raw_data:
                SHARED_STATE["status"]["fan"] = "ON" if str(raw_data["R4"]) == "1" else "OFF"
            
            if "cf" in raw_data:
                cf_raw = raw_data["cf"]
                SHARED_STATE["cf"]["v12"] = cf_raw.get("v12", SHARED_STATE["cf"]["v12"])
                SHARED_STATE["cf"]["v5"] = cf_raw.get("v5", SHARED_STATE["cf"]["v5"])
                SHARED_STATE["cf"]["v5sb"] = cf_raw.get("v5sb", SHARED_STATE["cf"]["v5sb"])

    except Exception as e:
        print(f"[ERROR Listener]: {e}")

# Start background thread loop for MQTT
mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start() 

@app.post("/api/control")
def control_device(req: ControlRequest):
    if req.device not in DEVICE_MAP or req.device == "calibrator" or req.state not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Parameter control isn't valid")
    
    result = sender.send_command(req.device, req.state)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["detail"])
    return result

@app.post("/api/calibrate")
def calibrate_sensors(req: CalibrationRequest):
    cf_data = {}
    if req.v12 is not None: cf_data["v12"] = req.v12
    if req.v5 is not None: cf_data["v5"] = req.v5
    if req.v5sb is not None: cf_data["v5sb"] = req.v5sb
    
    if not cf_data:
        raise HTTPException(status_code=400, detail="At least one voltage error parameter required")

    result = sender.send_command("calibrator", cf_data)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["detail"])
    return result

@app.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    await websocket.accept()
    print("[-] Client connected to telemetry websocket channel")
    
    try:
        while True:
            # Streams data instantly from memory without file I/O operations
            await websocket.send_json(SHARED_STATE)
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        print("[-] Client disconnected from telemetry websocket channel")
    except Exception as e:
        print(f"[!] WebSocket loop error: {e}")