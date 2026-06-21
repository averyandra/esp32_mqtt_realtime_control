import os
from dotenv import load_dotenv 

load_dotenv("../.env")

MQTT_BROKER = os.getenv("MQTT_BROKER")  # IP MQTT Broker
MQTT_PORT = int(os.getenv("MQTT_PORT"))

# topic
TOPIC_TELEMETRY = os.getenv("TOPIC_TELEMETRY") 
TOPIC_STATUS = os.getenv("TOPIC_STATUS") 
TOPIC_CONTROL_PREFIX = os.getenv("TOPIC_CONTROL_PREFIX") 

# local cache file
STATE_FILE = os.getenv("STATE_FILE") 
