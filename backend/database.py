import sqlite3
import os

DB_NAME = "telemetry.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            is_predicted INTEGER NOT NULL,
            timestamp REAL NOT NULL
        )
    ''')
    # Create an index on timestamp for faster ordering queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON positions (timestamp)')
    conn.commit()
    conn.close()

def insert_position(node_id, lat, lon, is_predicted, timestamp):
    # check_same_thread=False is perfectly fine here since we open and close immediately.
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO positions (node_id, lat, lon, is_predicted, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (node_id, lat, lon, int(is_predicted), timestamp))
    conn.commit()
    conn.close()

def get_recent_history(limit_per_node=50):
    """Returns the history grouped by node."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT node_id, lat, lon, is_predicted, timestamp 
        FROM positions 
        ORDER BY timestamp ASC
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    history = {}
    for r in rows:
        node_id = r[0]
        if node_id not in history:
            history[node_id] = []
        history[node_id].append({
            "lat": r[1],
            "lon": r[2],
            "is_predicted": bool(r[3]),
            "timestamp": r[4]
        })
        
    # Truncate arrays if they are longer than what the frontend intends to display at once
    for k in history.keys():
        history[k] = history[k][-limit_per_node:]
        
    return history
