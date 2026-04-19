import asyncio
import ssl
import os
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from data_processor import DataProcessor
import database

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"WS error: {e}")
                self.disconnect(connection)

manager = ConnectionManager()
processor = DataProcessor(manager)

# Load env config
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# MQTT Configuration
BROKER = "99f77a219ea44727a427f57478bab13f.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = os.getenv("HIVEMQ_USERNAME")
PASSWORD = os.getenv("HIVEMQ_PASSWORD")
TOPIC_BASE = "lora_telemetry"

mqtt_client = mqtt.Client(client_id="lora_backend_processor")

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(f"{TOPIC_BASE}/#")

def on_message(client, userdata, msg):
    # This runs in the MQTT background thread, but we need to call async processor
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    # Extract node_id from topic (e.g., lora_telemetry/node_alpha)
    parts = topic.split('/')
    if len(parts) >= 2:
        node_id = parts[1]
        # Schedule the async processing in the main event loop
        asyncio.run_coroutine_threadsafe(
            processor.process_payload(node_id, payload), 
            userdata['loop']
        )

@app.on_event("startup")
async def startup_event():
    # Initialize the local persistent storage table
    database.init_db()
    
    # Start the watchdog for dropped packets prediction
    processor.start()
    
    # Setup MQTT
    loop = asyncio.get_running_loop()
    mqtt_client.user_data_set({'loop': loop})
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    # Enable TLS for HiveMQ
    mqtt_client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
    mqtt_client.username_pw_set(USERNAME, PASSWORD)
    
    # Run MQTT loop in background thread
    mqtt_client.connect_async(BROKER, PORT, 60)
    mqtt_client.loop_start()

@app.on_event("shutdown")
async def shutdown_event():
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    
@app.get("/api/history")
def get_history(limit: int = 50):
    return database.get_recent_history(limit_per_node=limit)
    
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive and handle client messages if necessary
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
