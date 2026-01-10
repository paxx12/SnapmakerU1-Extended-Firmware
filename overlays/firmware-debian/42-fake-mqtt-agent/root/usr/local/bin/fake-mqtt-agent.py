#!/usr/bin/env python3

import sys
import json
import signal
import time
import random

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt not installed. Run: pip install paho-mqtt")
    sys.exit(1)

client = None

def log(msg):
    ts = time.strftime('%H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)

def publish_response(topic_suffix, payload):
    topic = f"mqtt_agent/response/{topic_suffix}"
    client.publish(topic, json.dumps(payload))
    log(f"Response to {topic}: {payload}")

def publish_notification(payload):
    topic = "mqtt_agent/notification"
    client.publish(topic, json.dumps(payload))
    log(f"Notification: {payload}")

def handle_update_device_status(request_id, params):
    publish_response("moonraker", {
        "error": {"code": -71, "message": "Failed to update device status"},
        "id": request_id,
        "jsonrpc": "2.0"
    })

def handle_set_link_mode(request_id, params):
    publish_response("moonraker_link", {
        "id": request_id,
        "jsonrpc": "2.0",
        "result": {"state": "success"}
    })

def handle_refresh_auth_code(request_id, params):
    pin_code = str(random.randint(10000000, 99999999))
    publish_response("moonraker_pin_code", {
        "id": request_id,
        "jsonrpc": "2.0",
        "result": {"pin_code": pin_code, "state": "success"}
    })

def handle_get_fw_latest(request_id, params):
    publish_response("system", {
        "id": request_id,
        "jsonrpc": "2.0",
        "result": {
            "data": {
                "authDevices": "[\"8110025060100014JGVC\"]",
                "createDate": "2025-12-31T02:26:31",
                "id": 5,
                "lastModifiedBy": "software@snapmaker.com",
                "modifiedDate": "2025-12-31T02:26:31",
                "name": "U1_1.0.0.158_20251230140122_upgrade.bin",
                "note": "https://public.resource.snapmaker.com/firmware/U1/U1_1.0.0.158_20251230140122_upgrade_firmware_desc.json",
                "status": 200,
                "url": "https://public.resource.snapmaker.com/firmware/U1/U1_1.0.0.158_20251230140122_upgrade.bin",
                "version": "1.0.0.158"
            },
            "state": "success"
        }
    })

METHODS = {
    "mqtt_agent.update_device_status": handle_update_device_status,
    "mqtt_agent.set_link_mode": handle_set_link_mode,
    "mqtt_agent.refresh_auth_code": handle_refresh_auth_code,
    "mqtt_agent.get_fw_latest": handle_get_fw_latest,
}

def on_connect(c, userdata, flags, rc):
    if rc == 0:
        log("Connected to MQTT broker")
        c.subscribe("mqtt_agent/request/#")
        log("Subscribed to mqtt_agent/request/#")
    else:
        log(f"Connection failed: {rc}")

def on_message(c, userdata, msg):
    request_id = None
    try:
        payload = msg.payload.decode('utf-8')
        log(f"Request on {msg.topic}: {payload}")
        req = json.loads(payload)

        request_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method in METHODS:
            METHODS[method](request_id, params)
        else:
            log(f"Unknown method: {method}")
    except json.JSONDecodeError as e:
        log(f"Invalid JSON: {e}")
    except Exception as e:
        log(f"Error handling message: {e}")

def main():
    global client

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    def shutdown(signum, frame):
        log("Shutting down...")
        client.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    log("Connecting to localhost:1883")
    client.connect("localhost", 1883, 60)

    log("Starting MQTT loop")
    client.loop_forever()

if __name__ == '__main__':
    main()
