import asyncio
import json
import os
import aiofiles
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from config import STATE_FILE
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

class ControlRequest(BaseModel):
    device: str  
    state: str   

class CalibrationRequest(BaseModel):
    v12: float = None
    v5: float = None
    v5sb: float = None

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
    # Pack parameters sent from dashboard UI
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
    print(f"[-] Client connected to telemetry websocket channel")
    
    fallback_data = {
        "telemetry": {"12v": 0.0, "5v": 0.0, "5vsb": 0.0, "pg": 0, "env": {"temp": 0.0, "hum": 0, "pres": 0.0}},
        "status": {"lamp": "OFF", "led": "OFF", "rack_led": "OFF", "fan": "OFF"},
        "cf": {"v12": 1.0, "v5": 1.0, "v5sb": 1.0}
    }
    
    try:
        while True:
            current_data = None
            if os.path.exists(STATE_FILE):
                try:
                    async with aiofiles.open(STATE_FILE, mode='rb') as f:
                        raw_bytes = await f.read()
                        if raw_bytes:
                            current_data = json.loads(raw_bytes.decode('utf-8'))
                except Exception:
                    pass
            
            if not current_data:
                current_data = fallback_data
            else:
                if "telemetry" not in current_data: current_data["telemetry"] = fallback_data["telemetry"]
                if "status" not in current_data: current_data["status"] = fallback_data["status"]
                if "cf" not in current_data: current_data["cf"] = fallback_data["cf"]

            await websocket.send_json(current_data)
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        print("[-] Client disconnected from telemetry websocket channel")
    except Exception as e:
        print(f"[!] WebSocket loop error: {e}")