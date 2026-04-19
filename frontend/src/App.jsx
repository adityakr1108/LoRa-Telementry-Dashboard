import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, Polyline } from 'react-leaflet';
import L from 'leaflet';
import './App.css';

// Fix for default leaflet icons not showing in React Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// A component to automatically pan the map to the latest node position
const RecenterAutomatically = ({ lat, lon }) => {
  const map = useMap();
  useEffect(() => {
    if (lat && lon) {
      map.setView([lat, lon], map.getZoom(), {
        animate: true,
        duration: 0.5
      });
    }
  }, [lat, lon, map]);
  return null;
}

function App() {
  const [nodes, setNodes] = useState({});
  const [trails, setTrails] = useState({}); // To draw path
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null); // Just for debug UI

  useEffect(() => {
    // Fetch historical data from SQLite database to pre-populate map
    fetch('https://lora-telementry-dashboard.onrender.com/api/history?limit=100')
      .then(res => res.json())
      .then(history => {
        setTrails(prevTrails => {
          const initialTrails = { ...prevTrails };
          Object.keys(history).forEach(node_id => {
            if (!initialTrails[node_id]) {
              initialTrails[node_id] = history[node_id].map(p => [p.lat, p.lon]);
            }
          });
          return initialTrails;
        });
        
        setNodes(prevNodes => {
          const initialNodes = { ...prevNodes };
          Object.keys(history).forEach(node_id => {
            const points = history[node_id];
            if (points.length > 0 && !initialNodes[node_id]) {
              initialNodes[node_id] = points[points.length - 1];
              initialNodes[node_id].node_id = node_id;
            }
          });
          return initialNodes;
        });
      })
      .catch(err => console.error("Could not load history from DB:", err));
  }, []);

  useEffect(() => {
    // Attempt WebSocket connection
    const ws = new WebSocket('wss://lora-telementry-dashboard.onrender.com/ws');

    ws.onopen = () => {
      console.log('Connected to Backend WebSocket');
      setIsConnected(true);
    };

    ws.onclose = () => {
      console.log('Disconnected from Backend WebSocket');
      setIsConnected(false);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setLastMessage(data);
      
      setNodes((prevNodes) => ({
        ...prevNodes,
        [data.node_id]: data,
      }));

      // Update trail history (keep last 50 points)
      setTrails((prevTrails) => {
        const currentTrail = prevTrails[data.node_id] || [];
        const newTrail = [...currentTrail, [data.lat, data.lon]];
        if (newTrail.length > 50) newTrail.shift();
        return {
          ...prevTrails,
          [data.node_id]: newTrail,
        };
      });
    };

    return () => {
      ws.close();
    };
  }, []);

  // NYC center by default
  const defaultCenter = [40.7128, -74.0060];
  
  // Get active node to center map (if any)
  const firstNodeId = Object.keys(nodes)[0];
  const activeNode = firstNodeId ? nodes[firstNodeId] : null;

  return (
    <div className="app-container">
      <div className="dashboard-overlay">
        <div className="glass-panel">
          <h2>LoRa Overwatch</h2>
          <div className="status-indicator">
            <span className={`status-dot ${isConnected ? 'online' : 'offline'}`}></span>
            {isConnected ? 'LIVE FEED' : 'DISCONNECTED'}
          </div>
          
          <div className="metrics-container">
            {Object.values(nodes).map((node) => (
              <div key={node.node_id} className={`node-card ${node.is_predicted ? 'warning' : 'ok'}`}>
                <h3>Node: {node.node_id.toUpperCase()}</h3>
                <p>Status: {node.is_predicted ? 'ESTIMATING (Packet Loss)' : 'VERIFIED'}</p>
                <p>LAT: {node.lat.toFixed(6)}</p>
                <p>LON: {node.lon.toFixed(6)}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <MapContainer 
        center={defaultCenter} 
        zoom={18} 
        scrollWheelZoom={true} 
        className="map-container"
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        
        {activeNode && (
          <RecenterAutomatically lat={activeNode.lat} lon={activeNode.lon} />
        )}

        {Object.values(nodes).map((node) => {
          // Create a dynamic HTML marker based on state
          const isPredicted = node.is_predicted;
          
          const customMarkerHTML = `
            <div class="tracker-dot ${isPredicted ? 'predicted' : 'actual'}">
              <div class="marker-label">${node.node_id}</div>
            </div>
          `;
          
          const customIcon = L.divIcon({
            html: customMarkerHTML,
            className: 'custom-div-icon',
            iconSize: [16, 16],
            iconAnchor: [8, 8] // Center the dot
          });

          return (
            <React.Fragment key={node.node_id}>
              {trails[node.node_id] && (
                <Polyline 
                  positions={trails[node.node_id]} 
                  pathOptions={{ 
                    color: isPredicted ? '#ffae42' : '#00ff7f', 
                    weight: 3, 
                    opacity: 0.6,
                    dashArray: isPredicted ? '5, 5' : null 
                  }} 
                />
              )}
              <Marker position={[node.lat, node.lon]} icon={customIcon}>
                <Popup>
                  <strong>{node.node_id}</strong><br/>
                  State: {isPredicted ? 'Predicting / Interpolating' : 'Direct Signal'}<br/>
                  Last Update: {new Date(node.timestamp * 1000).toLocaleTimeString()}
                </Popup>
              </Marker>
            </React.Fragment>
          );
        })}
      </MapContainer>
    </div>
  );
}

export default App;
