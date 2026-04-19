import numpy as np
from filterpy.kalman import KalmanFilter

class LoraKalmanFilter:
    def __init__(self, dt=1.0):
        # 4 state variables (lat, lon, v_lat, v_lon), 2 measurements (lat, lon)
        self.kf = KalmanFilter(dim_x=4, dim_z=2)
        
        # State transition matrix
        self.kf.F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1,  0],
            [0, 0, 0,  1]
        ])
        
        # Measurement function
        self.kf.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])
        
        # Measurement uncertainty (R) - can be tuned based on LoRa GPS noise
        self.kf.R = np.array([
            [0.0001, 0],
            [0, 0.0001]
        ])
        
        # Process uncertainty / Process Noise (Q)
        # Represents how much the node's velocity might randomly change
        q = 0.00001
        self.kf.Q = np.array([
            [q, 0, q, 0],
            [0, q, 0, q],
            [0, 0, q, 0],
            [0, 0, 0, q]
        ])
        
        # Initial State Covariance (P)
        self.kf.P *= 1000.0 
        
        self.initialized = False

    def initialize_state(self, lat, lon):
        # Initial state: lat, lon, v_lat=0, v_lon=0
        self.kf.x = np.array([[lat], [lon], [0.0], [0.0]])
        self.initialized = True

    def predict(self):
        """Predicts the next state using the model (no new measurement)."""
        if not self.initialized:
            return None, None
            
        self.kf.predict()
        return self.kf.x[0, 0], self.kf.x[1, 0]

    def update(self, lat, lon):
        """Updates the state with a new measurement."""
        if not self.initialized:
            self.initialize_state(lat, lon)
            return lat, lon
            
        # First predict using elapsed time
        self.kf.predict()
        # Then update with actual measurement
        self.kf.update(np.array([[lat], [lon]]))
        
        # Return the corrected state
        return self.kf.x[0, 0], self.kf.x[1, 0]

    def get_current_velocity(self):
        """Returns the current estimated velocity (v_lat, v_lon)."""
        if not self.initialized:
            return 0.0, 0.0
        return self.kf.x[2, 0], self.kf.x[3, 0]
