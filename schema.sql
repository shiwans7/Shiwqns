DROP TABLE IF EXISTS route_history;

CREATE TABLE route_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    timestamp TEXT NOT NULL, -- Format: YYYY-MM-DD HH:MM:SS
    speed REAL,
    fuel_level REAL,
    status TEXT
);

-- Optional: Add indexes for faster querying
CREATE INDEX IF NOT EXISTS idx_vehicle_id ON route_history (vehicle_id);
CREATE INDEX IF NOT EXISTS idx_timestamp ON route_history (timestamp);
