import json
import time
import asyncio
import re
from kalman_tracker import LoraKalmanFilter
import database

class NodeState:
    def __init__(self, node_id):
        self.node_id = node_id
        self.kf = LoraKalmanFilter(dt=1.0) # 1 second dt
        self.last_update_time = time.time()
        self.last_lat = None
        self.last_lon = None
        self.is_predicted = False

class DataProcessor:
    def __init__(self, websocket_manager):
        self.nodes = {}
        self.ws_manager = websocket_manager
        self.prediction_task = None

    def start(self):
        # Start a background loop to check for missing packets
        self.prediction_task = asyncio.create_task(self._watchdog_loop())

    async def _watchdog_loop(self):
        while True:
            await asyncio.sleep(1.0) # Tick every second
            current_time = time.time()
            for node_id, state in self.nodes.items():
                if not state.kf.initialized:
                    continue
                # If we haven't received an update in > 1.5 seconds, generate a prediction
                if current_time - state.last_update_time > 1.5:
                    await self._generate_prediction(state)

    async def _generate_prediction(self, state):
        # Missing or broken packet -> predict step
        pred_lat, pred_lon = state.kf.predict()
        if pred_lat is not None and pred_lon is not None:
            state.last_lat, state.last_lon = pred_lat, pred_lon
            state.is_predicted = True
            # Update the time so we don't spam predictions until next tick
            state.last_update_time = time.time()
            
            await self._broadcast_state(state)

    async def process_payload(self, node_id, payload_str):
        if node_id not in self.nodes:
            self.nodes[node_id] = NodeState(node_id)
        
        state = self.nodes[node_id]
        
        try:
            # Attempt to parse json
            data = json.loads(payload_str)
            
            if 'lat' in data and 'lon' in data:
                # Valid data packet!
                actual_lat = float(data['lat'])
                actual_lon = float(data['lon'])
                
                smoothed_lat, smoothed_lon = state.kf.update(actual_lat, actual_lon)
                state.last_lat = smoothed_lat
                state.last_lon = smoothed_lon
                state.last_update_time = time.time()
                state.is_predicted = False
                
                await self._broadcast_state(state)
            else:
                # JSON parsed but missing fields (fragmented)
                await self._generate_prediction(state)
                
        except json.JSONDecodeError:
            # Heuristic Auto-Correction
            # Attempt to fix the string by appending missing closing braces or quotes
            corrected_str = payload_str.strip()
            if not corrected_str.endswith("}"):
                if corrected_str.endswith(","):
                    corrected_str = corrected_str[:-1]
                corrected_str += "}"
            
            try:
                # Second attempt after appending footer
                data = json.loads(corrected_str)
                if 'lat' in data and 'lon' in data:
                    print(f"[{node_id}] Auto-corrected payload: {payload_str} -> {corrected_str}")
                    actual_lat = float(data['lat'])
                    actual_lon = float(data['lon'])
                    
                    smoothed_lat, smoothed_lon = state.kf.update(actual_lat, actual_lon)
                    state.last_lat = smoothed_lat
                    state.last_lon = smoothed_lon
                    state.last_update_time = time.time()
                    state.is_predicted = False
                    await self._broadcast_state(state)
                else:
                    print(f"[{node_id}] Auto-corrected but missing data: {corrected_str}. Predicting...")
                    await self._generate_prediction(state)
            except json.JSONDecodeError:
                # Extraction fallback using Regex if JSON structure fixing failed entirely
                lat_match = re.search(r'"lat"\s*:\s*(-?\d+(\.\d+)?)', payload_str)
                lon_match = re.search(r'"lon"\s*:\s*(-?\d+(\.\d+)?)', payload_str)
                
                if lat_match and lon_match:
                    print(f"[{node_id}] Regex extracted parts from broken payload: {payload_str}")
                    actual_lat = float(lat_match.group(1))
                    actual_lon = float(lon_match.group(1))
                    
                    smoothed_lat, smoothed_lon = state.kf.update(actual_lat, actual_lon)
                    state.last_lat = smoothed_lat
                    state.last_lon = smoothed_lon
                    state.last_update_time = time.time()
                    state.is_predicted = False
                    await self._broadcast_state(state)
                else:
                    # Fragmented / Broken JSON completely
                    print(f"[{node_id}] Failed to parse/correct payload: {payload_str}. Predicting...")
                    await self._generate_prediction(state)

    async def _broadcast_state(self, state):
        if state.last_lat is None or state.last_lon is None:
            return
            
        # 1. Save to Database for geospatial persistent history
        database.insert_position(
            state.node_id, 
            state.last_lat, 
            state.last_lon, 
            state.is_predicted, 
            state.last_update_time
        )
            
        # 2. Broadcast live to active web clients
        message = {
            "node_id": state.node_id,
            "lat": state.last_lat,
            "lon": state.last_lon,
            "is_predicted": state.is_predicted,
            "timestamp": state.last_update_time
        }
        await self.ws_manager.broadcast(json.dumps(message))

