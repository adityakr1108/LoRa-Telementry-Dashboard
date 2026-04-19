import json
import random
import time
import ssl
import os
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

# Load env variables from root directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Configuration
BROKER = "99f77a219ea44727a427f57478bab13f.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = os.getenv("HIVEMQ_USERNAME")
PASSWORD = os.getenv("HIVEMQ_PASSWORD")
TOPIC_BASE = "lora_telemetry"

def generate_trajectory():
    # Generate a dummy trajectory (e.g., walking/driving in a city)
    lat, lon = 40.7128, -74.0060 # NYC
    
    while True:
        # Move slightly
        lat += random.uniform(-0.0002, 0.0002)
        lon += random.uniform(-0.0002, 0.0002)
        yield lat, lon

def main():
    client = mqtt.Client(client_id="lora_simulator_rnd")
    
    # Enable TLS for HiveMQ
    client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.username_pw_set(USERNAME, PASSWORD)
    
    print(f"Connecting to {BROKER}...")
    client.connect(BROKER, PORT, 60)
    
    node_id = "node_alpha"
    trajectory = generate_trajectory()
    
    print("Starting simulation... Publishing to", f"{TOPIC_BASE}/{node_id}")
    
    try:
        while True:
            lat, lon = next(trajectory)
            
            # Simulate different transmission scenarios
            # 70% chance of standard valid packet
            # 15% chance of broken packet string
            # 15% chance of missing packet (simulates drop)
            
            scenario = random.random()
            topic = f"{TOPIC_BASE}/{node_id}"
            
            if scenario < 0.70:
                # Valid
                payload = json.dumps({"lat": lat, "lon": lon})
                client.publish(topic, payload)
                print(f"Sent Valid: {payload}")
                
            elif scenario < 0.85:
                # Broken / fragment
                # E.g., cut off the string
                valid_payload = json.dumps({"lat": lat, "lon": lon})
                broken_payload = valid_payload[:len(valid_payload) // 2]
                client.publish(topic, broken_payload)
                print(f"Sent Broken: {broken_payload}")
                
            else:
                # Dropped entirely
                print("Simulated Drop (no publish)")
                
            time.sleep(1) # 1 Hertz transmission
            
    except KeyboardInterrupt:
        print("Simulation stopped.")
        client.disconnect()

if __name__ == "__main__":
    main()
