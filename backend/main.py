import asyncio
import json
import os
import aiofiles
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from config import STATE_FILE
import sender

app = FastAPI(title="title")

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

@app.post("/api/control")
def control_device(req: ControlRequest):
    if req.device not in ["lamp", "led", "fan"] or req.state not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Parameter control isnt valid")
    
    result = sender.send_command(req.device, req.state)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["detail"])
    return result

@app.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    await websocket.accept()
    print(f"[-] client connected to websocket")
    
    fallback_data = {
        "telemetry": {"12v": 0.0, "5v": 0.0, "5vsb": 0.0, "pg": 0, "env": {"temp": 0.0, "hum": 0, "pres": 0.0}},
        "status": {"lamp": "OFF", "led": "OFF", "fan": "OFF"}
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
                if "telemetry" not in current_data or not current_data["telemetry"]:
                    current_data["telemetry"] = fallback_data["telemetry"]
                if "status" not in current_data or not current_data["status"]:
                    current_data["status"] = fallback_data["status"]

            await websocket.send_json(current_data)
            
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        print("[-] client disconnected from websocket")
    except Exception as e:
        print(f"[!] warn idk why: {e}")
