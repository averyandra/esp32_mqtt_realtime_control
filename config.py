# config.py
MQTT_BROKER = "10.0.0.1"  # IP Mini Server Armbian
MQTT_PORT = 1883

TOPIC_TELEMETRY = "vorsa/psu/telemetry"
TOPIC_STATUS = "vorsa/psu/status"
TOPIC_CONTROL_PREFIX = "vorsa/control/"

# File cache lokal untuk menjembatani data dari Listener ke FastAPI/AI Agent
STATE_FILE = "/tmp/vorsa_latest_state.json"
