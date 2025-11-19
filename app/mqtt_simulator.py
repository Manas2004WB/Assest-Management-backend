import asyncio
import json
import random
from datetime import datetime
import paho.mqtt.client as mqtt
from fastapi import FastAPI

app = FastAPI(title="IoT Simulator API")

# MQTT configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 9001       # WebSocket port
TOPIC_TEMPLATE = "node/{node_id}/metrics"

NODE_IDS = [1, 2, 3, 4, 5]

# Use WebSocket transport so frontend can subscribe
client = mqtt.Client(transport="websockets")

@app.on_event("startup")
async def startup_event():
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.loop_start()           # Required for async publishing
    asyncio.create_task(simulate_metrics())

async def simulate_metrics():
    while True:
        for node_id in NODE_IDS:
            data = {
                "temperature": round(random.uniform(20, 30), 1),
                "humidity": random.randint(30, 70),
                "pressure": random.randint(990, 1025),
                "status": random.choice(["OK", "Warning", "Error"]),
                "timestamp": datetime.utcnow().isoformat()
            }
            topic = TOPIC_TEMPLATE.format(node_id=node_id)
            client.publish(topic, json.dumps(data))
            print(f"Published to {topic}: {data}")
        await asyncio.sleep(2)

@app.get("/api/nodes")
def get_nodes():
    return NODE_IDS
