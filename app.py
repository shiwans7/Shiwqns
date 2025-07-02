from flask import Flask, render_template, jsonify, g, request
import random
import time
import sqlite3
import datetime
from math import radians, sin, cos, sqrt, atan2


app = Flask(__name__)
DATABASE = 'vehicle_monitoring.db'

# --- Maintenance Schedule Definition (Simulated) ---
MAINTENANCE_DEFINITIONS = {
    "Schimb ulei motor": {"km": 15000, "hours": 300, "description": "Înlocuirea uleiului de motor și a filtrului de ulei."},
    "Verificare plăcuțe frână": {"km": 20000, "description": "Inspecția vizuală și măsurarea grosimii plăcuțelor de frână."},
    "Înlocuire filtru aer": {"km": 30000, "hours": 600, "description": "Înlocuirea filtrului de aer al motorului."},
    "Înlocuire filtru combustibil": {"km": 40000, "description": "Înlocuirea filtrului de combustibil."},
    "Verificare și completare lichid răcire": {"hours": 500, "description": "Verificarea nivelului și stării lichidului de răcire."},
    "Inspecție generală": {"km": 10000, "hours": 250, "description": "Verificări generale: lumini, anvelope, scurgeri etc."}
}
# Store last service data in memory for simplicity for now.
# In a real app, this would come from a database.
# { "vehicle_id": { "service_name": {"km": last_km, "hours": last_hours}, ... } }
LAST_SERVICE_DATA = {}


# --- Database Setup ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
        print("Database initialized with schema.sql")


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id

# --- Utility Functions ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    if any(coord is None for coord in [lat1, lon1, lat2, lon2]):
        return 0
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    a = sin(dLat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dLon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# --- Vehicle Simulation ---
class Vehicle:
    def __init__(self, vehicle_id, initial_lat, initial_lon, fuel_capacity=100.0):
        self.vehicle_id = vehicle_id
        self.latitude = initial_lat
        self.longitude = initial_lon

        last_state = query_db("SELECT odometer, engine_hours, fuel_level FROM route_history WHERE vehicle_id = ? ORDER BY timestamp DESC LIMIT 1", (self.vehicle_id,), one=True)
        if last_state and last_state['odometer'] is not None:
            self.odometer = last_state['odometer']
            self.engine_hours = last_state['engine_hours'] if last_state['engine_hours'] is not None else 0
            self.fuel_level = last_state['fuel_level'] if last_state['fuel_level'] is not None else fuel_capacity
        else:
            self.odometer = random.randint(5000, 25000) # Start with lower initial values for more interesting maintenance
            self.engine_hours = random.randint(100, 500)
            self.fuel_level = random.uniform(fuel_capacity * 0.5, fuel_capacity)

        self.fuel_capacity = fuel_capacity
        self.speed = 0
        self.status = "idle"
        self.current_route_segment = [(initial_lat, initial_lon)]
        self.last_update_time = time.time()

    def update_data(self):
        current_time = time.time()
        time_delta_seconds = current_time - self.last_update_time
        if time_delta_seconds < 1:
            return
        self.last_update_time = current_time
        time_delta_hours = time_delta_seconds / 3600.0

        previous_lat, previous_lon = self.latitude, self.longitude
        distance_moved_km = 0

        if self.status == "moving" and self.fuel_level > 0:
            self.latitude += random.uniform(-0.005, 0.005) * (time_delta_seconds / 5.0)
            self.longitude += random.uniform(-0.01, 0.01) * (time_delta_seconds / 5.0)
            self.latitude = max(43.5, min(self.latitude, 48.5))
            self.longitude = max(20.0, min(self.longitude, 30.0))
            self.speed = random.uniform(30, 90)
            distance_moved_km = haversine(previous_lat, previous_lon, self.latitude, self.longitude)

            fuel_consumed_engine_on = 1.0 * time_delta_hours
            fuel_consumed_km = 0.15 * distance_moved_km
            self.fuel_level -= (fuel_consumed_engine_on + fuel_consumed_km)
            self.odometer += distance_moved_km
            self.engine_hours += time_delta_hours

        elif self.status == "idle":
            self.speed = 0
            self.fuel_level -= (1.0 * time_delta_hours)
            self.engine_hours += time_delta_hours

        if self.fuel_level < 0: self.fuel_level = 0
        if self.fuel_level == 0 and self.status != "out_of_fuel":
             self.status = "out_of_fuel"
             self.speed = 0

        if random.random() < (0.03 * (time_delta_seconds / 5.0)):
            if self.status == "idle" and self.fuel_level > self.fuel_capacity * 0.1:
                self.status = "moving"
            elif self.status == "moving":
                self.status = "idle"

        if (self.status in ["moving", "idle"] and time_delta_seconds > 2) or distance_moved_km > 0.001:
            self.current_route_segment.append((self.latitude, self.longitude))
            if len(self.current_route_segment) > 50: self.current_route_segment.pop(0)

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            execute_db(
                "INSERT INTO route_history (vehicle_id, latitude, longitude, timestamp, speed, fuel_level, status, odometer, engine_hours) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self.vehicle_id, self.latitude, self.longitude, timestamp, self.speed, self.fuel_level, self.status, self.odometer, self.engine_hours)
            )

    def to_dict(self):
        return {
            "vehicle_id": self.vehicle_id,
            "latitude": self.latitude, "longitude": self.longitude,
            "fuel_level": round(self.fuel_level, 2), "fuel_capacity": self.fuel_capacity,
            "speed": round(self.speed, 2), "status": self.status,
            "odometer": round(self.odometer, 2), "engine_hours": round(self.engine_hours, 2),
            "route_segment": self.current_route_segment
        }

vehicles_data = {}

def get_or_create_vehicles():
    global vehicles_data
    if not vehicles_data:
        initial_config = [
            {"id": "VS001", "lat": 44.43, "lon": 26.10, "fuel": 120},
            {"id": "VS002", "lat": 45.75, "lon": 21.22, "fuel": 80},
            {"id": "VS003", "lat": 46.77, "lon": 23.60, "fuel": 150},
            {"id": "VS004", "lat": 47.16, "lon": 27.58, "fuel": 100},
        ]
        for v_conf in initial_config:
            vehicles_data[v_conf["id"]] = Vehicle(v_conf["id"], v_conf["lat"], v_conf["lon"], v_conf["fuel"])
    return vehicles_data

@app.route('/')
def index():
    current_vehicles = get_or_create_vehicles()
    return render_template('index.html', vehicles=current_vehicles.values())

@app.route('/history')
def history_page():
    current_vehicles = get_or_create_vehicles()
    return render_template('history.html', vehicles=current_vehicles.values())

@app.route('/maintenance')
def maintenance_page():
    current_vehicles = get_or_create_vehicles()
    return render_template('maintenance.html', vehicles=current_vehicles.values())


@app.route('/api/vehicles')
def get_vehicles_data_api():
    current_vehicles = get_or_create_vehicles()
    for vehicle_obj in current_vehicles.values(): # Corrected variable name
        vehicle_obj.update_data()
    return jsonify([vehicle_obj.to_dict() for vehicle_obj in current_vehicles.values()])


@app.route('/api/vehicle/<string:vehicle_id>/history')
def get_vehicle_history(vehicle_id):
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    query_sql = "SELECT latitude, longitude, timestamp, speed, fuel_level, status, odometer, engine_hours FROM route_history WHERE vehicle_id = ?"
    params = [vehicle_id]
    if start_date_str:
        query_sql += " AND date(timestamp) >= date(?)"
        params.append(start_date_str)
    if end_date_str:
        query_sql += " AND date(timestamp) <= date(?)"
        params.append(end_date_str)
    query_sql += " ORDER BY timestamp ASC"
    history_data = query_db(query_sql, tuple(params))
    return jsonify([dict(row) for row in history_data])

@app.route('/api/vehicle/<string:vehicle_id>/operational_summary')
def get_operational_summary(vehicle_id):
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    conditions = " WHERE vehicle_id = ? "
    params = [vehicle_id]
    if start_date_str:
        conditions += " AND date(timestamp) >= date(?) "; params.append(start_date_str)
    if end_date_str:
        conditions += " AND date(timestamp) <= date(?) "; params.append(end_date_str)

    first_rec_q = f"SELECT odometer, engine_hours, timestamp FROM route_history {conditions} ORDER BY timestamp ASC LIMIT 1"
    last_rec_q = f"SELECT odometer, engine_hours, timestamp FROM route_history {conditions} ORDER BY timestamp DESC LIMIT 1"
    first_R = query_db(first_rec_q, tuple(params), one=True)
    last_R = query_db(last_rec_q, tuple(params), one=True)

    total_fuel_consumed_estimate, total_engine_hours_diff, total_distance_km = 0,0,0
    period_start_ts, period_end_ts = None, None

    if first_R and last_R:
        period_start_ts, period_end_ts = first_R['timestamp'], last_R['timestamp']
        if first_R['odometer'] is not None and last_R['odometer'] is not None:
            total_distance_km = round(last_R['odometer'] - first_R['odometer'], 2)
        if first_R['engine_hours'] is not None and last_R['engine_hours'] is not None:
             total_engine_hours_diff = round(last_R['engine_hours'] - first_R['engine_hours'], 2)
        if total_engine_hours_diff > 0:
            total_fuel_consumed_estimate = round(total_engine_hours_diff * 4.0, 2)

    return jsonify({
        "total_distance_km": total_distance_km, "total_fuel_consumed": total_fuel_consumed_estimate,
        "total_engine_hours": total_engine_hours_diff,
        "period_start_timestamp": period_start_ts, "period_end_timestamp": period_end_ts,
    })

@app.route('/api/vehicle/<string:vehicle_id>/maintenance_status')
def get_maintenance_status(vehicle_id):
    vehicle = vehicles_data.get(vehicle_id)
    if not vehicle:
        return jsonify({"error": "Vehicle not found"}), 404

    current_odometer = vehicle.odometer
    current_engine_hours = vehicle.engine_hours

    # Initialize vehicle in LAST_SERVICE_DATA if not present
    if vehicle_id not in LAST_SERVICE_DATA:
        LAST_SERVICE_DATA[vehicle_id] = {}

    schedule_status = []
    for service_name, intervals in MAINTENANCE_DEFINITIONS.items():
        # Get last serviced data, default to 0 if not found (first service)
        last_serviced_km = LAST_SERVICE_DATA[vehicle_id].get(service_name, {}).get("km", 0)
        last_serviced_hours = LAST_SERVICE_DATA[vehicle_id].get(service_name, {}).get("hours", 0)

        km_since_last = current_odometer - last_serviced_km
        hours_since_last = current_engine_hours - last_serviced_hours

        status_item = {
            "service_name": service_name,
            "description": intervals.get("description", ""),
            "last_serviced_km": last_serviced_km,
            "last_serviced_hours": last_serviced_hours,
            "current_odometer": current_odometer,
            "current_engine_hours": current_engine_hours,
            "km_since_last": km_since_last,
            "hours_since_last": hours_since_last,
            "km_interval": intervals.get("km"),
            "hours_interval": intervals.get("hours"),
            "next_km_due": None, "km_remaining": None,
            "next_hours_due": None, "hours_remaining": None,
        }

        if intervals.get("km"):
            status_item["next_km_due"] = last_serviced_km + intervals["km"]
            status_item["km_remaining"] = max(0, status_item["next_km_due"] - current_odometer)
        if intervals.get("hours"):
            status_item["next_hours_due"] = last_serviced_hours + intervals["hours"]
            status_item["hours_remaining"] = max(0, status_item["next_hours_due"] - current_engine_hours)

        schedule_status.append(status_item)

    return jsonify({
        "vehicle_id": vehicle_id,
        "current_odometer": current_odometer,
        "current_engine_hours": current_engine_hours,
        "maintenance_schedule": schedule_status
    })


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
