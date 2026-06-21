<?php 
$envFile = __DIR__ . '/../.env';
$config = [];

if (file_exists($envFile)) {
    $lines = file($envFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        // Ignore if line is a comment
        if (strpos(trim($line), '#') === 0) continue;
        
        // 3. Bug Fix: Make sure there is an '=' character in the line
        if (strpos($line, '=') !== false) {
            list($name, $value) = explode('=', $line, 2);
            $config[trim($name)] = trim(str_replace(['"', "'"], '', $value));
        }
    }
} else {
    // Debug message if the file is actually not found at that location
    echo "Warning: .env file not found in: " . realpath(__DIR__ . '/../') . "/.env <br>";
}
// Fallbacks if env file parameter is not found
$localApi = $config['LOCAL_API_URL'] ?? "http://api.localhost:8080";
$localWs  = $config['LOCAL_WS_URL']  ?? "ws://api.localhost:8080";
$prodApi  = $config['PROD_API_URL']  ?? "https://api.yourpublicdomain.com";
$prodWs   = $config['PROD_WS_URL']   ?? "wss://api.yourpublicdomain.com";

// test
// echo "Local API URL: " . $localApi;
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LAB Hub - Physical Interface Monitor</title>
    <style>
        :root {
            --bg-dark: #0a0a0a;
            --panel-bg: rgba(20, 20, 20, 0.6);
            --border-color: rgba(255, 0, 0, 0.15);
            --accent-red: #ff3333;
            --accent-red-dim: #990000;
            --text-main: #e0e0e0;
            --text-muted: #888888;
            --neon-shadow: 0 0 15px rgba(255, 51, 51, 0.4);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2rem;
            background-image: radial-gradient(circle at 50% 50%, #1a0505 0%, #0a0a0a 80%);
        }

        header {
            width: 100%;
            max-width: 1200px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }

        header h1 {
            font-size: 1.8rem;
            letter-spacing: 2px;
            color: #ffffff;
            text-shadow: 0 0 10px rgba(255, 51, 51, 0.5);
        }

        header h1 span {
            color: var(--accent-red);
        }

        .status-badge {
            background: rgba(255, 255, 255, 0.05);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 8px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #ff3333;
        }

        .status-dot.online {
            background-color: #00ff66;
            box-shadow: 0 0 8px #00ff66;
        }

        .main-container {
            width: 100%;
            max-width: 1200px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
        }

        .card {
            background: var(--panel-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .card:hover {
            border-color: rgba(255, 51, 51, 0.4);
        }

        .card h2 {
            font-size: 1.1rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .grid-data {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }

        .data-box {
            background: rgba(0, 0, 0, 0.3);
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.03);
        }

        .data-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-bottom: 0.25rem;
        }

        .data-value {
            font-size: 1.6rem;
            font-weight: bold;
            font-family: monospace;
            color: #ffffff;
        }

        .data-value.flash {
            color: var(--accent-red);
            text-shadow: 0 0 8px rgba(255, 51, 51, 0.6);
        }

        .control-list {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .control-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(0, 0, 0, 0.2);
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.02);
        }

        .control-info p {
            font-weight: bold;
            font-size: 0.95rem;
        }

        .control-info span {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .btn-toggle {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 0.6rem 1.2rem;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            font-size: 0.85rem;
            transition: all 0.2s ease;
            min-width: 80px;
            text-align: center;
        }

        .btn-toggle:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.2);
        }

        .btn-toggle.active {
            background: var(--accent-red);
            color: #ffffff;
            border-color: var(--accent-red);
            box-shadow: var(--neon-shadow);
        }

        .btn-toggle:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
    </style>
</head>
<body>

    <header>
        <h1>LAB <span>MONITOR</span></h1>
        <div class="status-badge">
            <div id="status-dot" class="status-dot"></div>
            <span id="status-text">DISCONNECTED</span>
        </div>
    </header>

    <main class="main-container">
        <section class="card">
            <h2>Electrical Telemetry</h2>
            <div class="grid-data">
                <div class="data-box">
                    <div class="data-label">+12V Rail</div>
                    <div id="v12-val" class="data-value">0.00 V</div>
                </div>
                <div class="data-box">
                    <div class="data-label">+5V Rail</div>
                    <div id="v5-val" class="data-value">0.00 V</div>
                </div>
                <div class="data-box">
                    <div class="data-label">5VSB Rail</div>
                    <div id="v5sb-val" class="data-value">0.00 V</div>
                </div>
                <div class="data-box">
                    <div class="data-label">POWER GOOD (PG)</div>
                    <div id="pg-val" class="data-value">0</div>
                </div>
            </div>
        </section>

        <section class="card">
            <h2>Environment Sensor</h2>
            <div class="grid-data">
                <div class="data-box">
                    <div class="data-label">ROOM TEMPERATURE</div>
                    <div id="temp-val" class="data-value">0.0 °C</div>
                </div>
                <div class="data-box">
                    <div class="data-label">HUMIDITY (RH)</div>
                    <div id="hum-val" class="data-value">0 %</div>
                </div>
                <div class="data-box" style="grid-column: span 2;">
                    <div class="data-label">BAROMETRIC PRESSURE</div>
                    <div id="pres-val" class="data-value">0.0 hPa</div>
                </div>
            </div>
        </section>

        <section class="card">
            <h2>Sovereign Actuators</h2>
            <div class="control-list">
                <div class="control-item">
                    <div class="control-info">
                        <p>Main Lab Lamp</p>
                        <span>Main Circuit AC Relay</span>
                    </div>
                    <button id="lamp-btn" class="btn-toggle" onclick="toggleDevice('lamp')">OFF</button>
                </div>
                <div class="control-item">
                    <div class="control-info">
                        <p>LED Strip</p>
                        <span>Workbench Secondary Light</span>
                    </div>
                    <button id="led-btn" class="btn-toggle" onclick="toggleDevice('led')">OFF</button>
                </div>
                <div class="control-item">
                    <div class="control-info">
                        <p>Rack LED</p>
                        <span>Server Cabinet Frame Lighting</span>
                    </div>
                    <button id="rack_led-btn" class="btn-toggle" onclick="toggleDevice('rack_led')">OFF</button>
                </div>
                <div class="control-item">
                    <div class="control-info">
                        <p>Exhaust Fan</p>
                        <span>Air Circulation System</span>
                    </div>
                    <button id="fan-btn" class="btn-toggle" onclick="toggleDevice('fan')">OFF</button>
                </div>
            </div>
        </section>
    </main>

    <script>
        // --- CLIENT SIDE DOMAIN SCANNING AND ROUTING LOGIC ---
        const currentHost = window.location.host;
        let apiBase = "<?= $localApi; ?>";
        let wsBase = "<?= $localWs; ?>";

        // Route dynamically based on the browser address parsing
        if (currentHost === "monitor.vorsa-lab.my.id") {
            apiBase = "<?= $prodApi; ?>";
            wsBase = "<?= $prodWs; ?>";
        } else if (currentHost === "vorsa.lab:8081") {
            apiBase = "<?= $localApi; ?>";
            wsBase = "<?= $localWs; ?>";
        }

        const WS_URL = `${wsBase}/ws/monitor`;
        const API_URL = `${apiBase}/api/control`;

        let ws = null;
        let reconnectTimeout = null;

        // Internal tracking states synced with devices.py mapping schema
        const deviceStates = {
            lamp: "OFF",
            led: "OFF",
            rack_led: "OFF",
            fan: "OFF"
        };

        // --- WEBSOCKET COMMUNICATION CIRCUIT ---
        function connectWebSocket() {
            console.log(`[-] Synchronizing pipeline to destination target: ${WS_URL}`);
            ws = new WebSocket(WS_URL);

            ws.onopen = () => {
                console.log("[-] Communication circuit successfully opened.");
                document.getElementById("status-dot").classList.add("online");
                document.getElementById("status-text").innerText = "LIVE CONNECTED";
                if (reconnectTimeout) clearTimeout(reconnectTimeout);
            };

            ws.onmessage = (event) => {
                try {
                    const payload = JSON.parse(event.data);
                    
                    const telemetry = payload?.telemetry || {};
                    const env = telemetry?.env || {};
                    const status = payload?.status || {};

                    // 1. Process ATX PSU Electrical Parameters
                    updateDOMText("v12-val", telemetry["12v"], " V", true);
                    updateDOMText("v5-val", telemetry["5v"], " V", true);
                    updateDOMText("v5sb-val", telemetry["5vsb"], " V", true);
                    
                    const pgElement = document.getElementById("pg-val");
                    if (pgElement) {
                        const pgValue = telemetry["pg"];
                        pgElement.innerText = pgValue === 1 ? "GOOD (1)" : `FAIL (${pgValue || 0})`;
                        pgElement.style.color = (pgValue === 1) ? "#00ff66" : "var(--accent-red)";
                    }

                    // 2. Process Environmental Sensors Payload
                    updateDOMText("temp-val", env["temp"], " °C", false, 1);
                    updateDOMText("hum-val", env["hum"], " %", false, 0);
                    updateDOMText("pres-val", env["pres"], " hPa", false, 1);

                    // 3. Sync Actuator Status States mapping with Python listener cache
                    syncButtonUI("lamp", status["lamp"]);
                    syncButtonUI("led", status["led"]);
                    syncButtonUI("rack_led", status["rack_led"]);
                    syncButtonUI("fan", status["fan"]);

                } catch (err) {
                    console.error("[!] Parse error handling message packet data:", err);
                }
            };

            ws.onclose = () => {
                console.warn("[!] Connection severed. Attempting safe automated reconnection loop...");
                document.getElementById("status-dot").classList.remove("online");
                document.getElementById("status-text").innerText = "DISCONNECTED";
                
                clearTimeout(reconnectTimeout);
                reconnectTimeout = setTimeout(connectWebSocket, 3000);
            };

            ws.onerror = (err) => {
                console.error("[!] Connection circuit error encounter:", err);
                ws.close();
            };
        }

        // --- DOM MANIPULATION & INTERFACE RENDERERS ---
        function updateDOMText(elementId, value, unit = "", isVoltage = false, precision = 2) {
            const el = document.getElementById(elementId);
            if (!el) return;

            const numValue = parseFloat(value) || 0.0;
            const textResult = numValue.toFixed(precision) + unit;

            // Trigger visual glow effect if value state switches
            if (el.innerText !== textResult && numValue > 0.1) {
                el.innerText = textResult;
                el.classList.add("flash");
                setTimeout(() => el.classList.remove("flash"), 250);
            } else {
                el.innerText = textResult;
            }
        }

        function syncButtonUI(device, stateFromBroker) {
            if (!stateFromBroker) return;
            const btn = document.getElementById(`${device}-btn`);
            if (!btn) return;

            deviceStates[device] = stateFromBroker;
            btn.innerText = stateFromBroker;

            if (stateFromBroker === "ON") {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        }

        // --- BACKEND API INTERACTION ENGINE ---
        function toggleDevice(device) {
            const btn = document.getElementById(`${device}-btn`);
            const currentState = deviceStates[device];
            const targetState = currentState === "ON" ? "OFF" : "ON";

            // Prevent double submission triggers during pipeline transaction
            if (btn) btn.disabled = true;

            console.log(`[-] Dispatching command execution payload: ${device} -> ${targetState}`);

            fetch(API_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    device: device,
                    state: targetState
                })
            })
            .then(res => {
                if (!res.ok) throw new Error(`HTTP Error Status: ${res.status}`);
                return res.json();
            })
            .then(data => {
                console.log(`[-] Execution transmission success for ${device}:`, data);
                // Optimistic UI updates to secure immediate transition state rendering
                syncButtonUI(device, targetState);
            })
            .catch(err => {
                console.error(`[!] Failed executing terminal control sequence on target ${device}:`, err);
                alert(`Command execution sequence failed for device channel: ${device}`);
            })
            .finally(() => {
                // Unlock element access once transmission clears
                if (btn) btn.disabled = false;
            });
        }

        window.onload = connectWebSocket;
    </script>
</body>
</html>