# device_list = ["R1", "R2", "R3", "R4"]
# List of raw device names used for internal validation / array loops
device_list = ["lamp", "led", "rack_led", "fan", "calibrator", "all"]

DEVICE_MAP = {
    "lamp": "R1",
    "led": "R2",
    "rack_led": "R3",
    "fan": "R4",
    "calibrator": "CF",
    "all": "all"
}