# LoRa Overwatch

LoRa Overwatch is a real-time, fault-tolerant geospatial tracking dashboard designed to reconstruct fragmented telemetry data from remote LoRa (Long Range) nodes. 

Built for tactical and remote setups where packet drops and string corruption are extremely common, this system features an intelligent "healing" layer. It uses heuristic string extraction and mathematical **Kalman Filter** predictions to accurately estimate a moving asset's location during radio "dead zones," ensuring your operational dashboard never stutters or loses visual continuity.

![Tech Stack](https://img.shields.io/badge/Tech_Stack-FastAPI_|_React_|_Leaflet_|_Kalman_Filters-blue?style=for-the-badge)

## Core Features
1. **Packet Fragmentation Detection & Auto-Correction**: Detects incomplete JSON strings cut off by poor radio bandwidth and auto-appends syntax closures or uses Regular Expressions to salvage coordinate numbers from the raw noise.
2. **Predictive State Estimation**: Uses a `filterpy` Kalman Filter. If a packet is entirely dropped by the network, the backend utilizes the $t-1$ and $t-2$ velocities to accurately project where the node should be.
3. **Visual Continuity Pipeline**: Distinguishes between verified coordinates (Solid Spring Green) and mathematically estimated coordinates (Pulsing Amber) in real-time.
4. **Geospatial SQLite Database**: Permanently logs every coordinate (actual or predicted) to a local SQLite database file (`telemetry.db`) so the map instantly loads the node's full "pattern of life" historical trail upon refresh.

## Architecture Structure
```text
├── backend/
│   ├── database.py       # SQLite Persistence Layer
│   ├── data_processor.py # Heuristic Auto-Correction & Prediction Engine
│   ├── kalman_tracker.py # Mathematical State estimation
│   ├── server.py         # FastAPI WebSockets & REST logic
│   └── simulator.py      # MQTT Publisher that simulates dropped/broken signals
├── frontend/
│   ├── src/App.jsx       # Real-time Mapbox/Leaflet UI
│   └── src/App.css       # Glassmorphism Overwatch styling
```

---

## How to Run Locally

### 1. Start the Backend Server
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start the LoRa Signal Simulator
In a second terminal:
```bash
cd backend
.\venv\Scripts\Activate.ps1
python simulator.py
```

### 3. Start the Frontend Dashboard
In a third terminal:
```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:5173` to view the live dashboard!

---

## How to Make It Live (Production Deployment)

To move this from your local computer to the World Wide Web so you can access it on your phone or share it with a team, you need to deploy all three major components of the architecture:

### Step 1: Claim a Production MQTT Broker
Currently, the system is hardcoded to use `test.mosquitto.org`. Since that is a public sandbox, anyone can see your data.
- **Go to [HiveMQ Cloud](https://www.hivemq.com/mqtt-cloud-broker/)** and sign up for their free Serverless cluster.
- They will give you a secure `URL`, `Port`, `Username`, and `Password`.
- **Change the code:** Update `backend/server.py` and `backend/simulator.py` to use these secure credentials in the `mqtt_client.connect()` configuration!

### Step 2: Deploy the FastAPI Backend
For backend python apps with WebSockets and databases, a strong Platform-as-a-Service (PaaS) is recommended.
- **Go to [Render.com](https://render.com) or [Railway.app](https://railway.app)**.
- Connect your GitHub repository.
- Select the `backend/` folder.
- Set the Build Command to `pip install -r requirements.txt`.
- Set the Start Command to `uvicorn server:app --host 0.0.0.0 --port 8000`.
- **Warning:** Because Render/Railway server disks are ephemeral (they reset on redeploy), you will eventually want to swap the internal SQLite `telemetry.db` connection in `database.py` to an external PostgreSQL database (like Supabase or Render's free PostgreSQL tier) so your history isn't deleted when the server restarts.
- Once deployed, it will give you a URL like `https://lora-backend.onrender.com`.

### Step 3: Deploy the React Frontend
- Inside `frontend/src/App.jsx`, update the two `localhost` URLs:
  - Change the WebSocket URL to `wss://lora-backend.onrender.com/ws` *(wss stands for secure websocket)*.
  - Change the database Fetch URL to `https://lora-backend.onrender.com/api/history`.
- Push the changes to GitHub.
- **Go to [Vercel.com](https://vercel.com) or [Netlify.com](https://netlify.com)**.
- Import your repository and select the `frontend/` directory. Vercel will auto-detect Vite and build it automatically.
- Once finished, Vercel will give you a live production website URL!

Your hardware LoRa nodes in the forest will now beam data to HiveMQ, which feeds Render's Python backend, which powers Vercel's tactical dashboard globally!
