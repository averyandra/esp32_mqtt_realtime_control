import asyncio
import json
import os
import aiofiles  # Menggunakan async I/O untuk mem-bypass Page Cache Linux
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from config import STATE_FILE
import sender

app = FastAPI(title="VORSA Lab Core Network - Async File Engine")

# Izinkan CORS penuh untuk interkoneksi lab
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ControlRequest(BaseModel):
    device: str  # 'lampu', 'led', 'fan'
    state: str   # 'ON', 'OFF'

# --- API ENDPOINT UNTUK KENDALI AKTUATOR ---
@app.post("/api/control")
def control_device(req: ControlRequest):
    if req.device not in ["lampu", "led", "fan"] or req.state not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Parameter sirkuit kontrol tidak valid")
    
    result = sender.send_command(req.device, req.state)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["detail"])
    return result

# --- WEBSOCKET REALTIME ROUTE (ASYNC FILE READER) ---
@app.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    await websocket.accept()
    print(f"[-] Client terhubung ke sirkuit WebSocket VORSA")
    
    # Baseline data jika berkas belum terbuat di disk
    fallback_data = {
        "telemetry": {"12v": 0.0, "5v": 0.0, "5vsb": 0.0, "pg": 0, "env": {"temp": 0.0, "hum": 0, "pres": 0.0}},
        "status": {"lampu_utama": "OFF", "led_strip": "OFF", "exhaust_fan": "OFF"}
    }
    
    try:
        while True:
            current_data = None
            
            if os.path.exists(STATE_FILE):
                try:
                    # Membuka file secara asynchronous dan memaksa pembacaan ulang sektor disk.
                    # Mode binary 'rb' digunakan untuk mematikan internal text buffering milik Python.
                    async with aiofiles.open(STATE_FILE, mode='rb') as f:
                        raw_bytes = await f.read()
                        if raw_bytes:
                            current_data = json.loads(raw_bytes.decode('utf-8'))
                except Exception:
                    # Mengamankan tabrakan (race condition) jika di milidetik yang sama listener.py sedang menulis file
                    pass
            
            # Validasi kelengkapan struktur data agar JavaScript tidak mengalami silent error
            if not current_data:
                current_data = fallback_data
            else:
                if "telemetry" not in current_data or not current_data["telemetry"]:
                    current_data["telemetry"] = fallback_data["telemetry"]
                if "status" not in current_data or not current_data["status"]:
                    current_data["status"] = fallback_data["status"]

            # Kirim data paling segar ke browser via WebSocket
            await websocket.send_json(current_data)
            
            # Interval penyedotan data disamakan dengan refresh rate data ESP32 (500ms)
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        print("[-] Client memutus koneksi WebSocket VORSA")
    except Exception as e:
        print(f"[!] Gangguan pada loop WebSocket: {e}")
