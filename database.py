import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect("stolen_vehicles.db")
    cursor = conn.cursor()
    
    # Stolen Vehicles Registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stolen_vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT UNIQUE NOT NULL,
            owner_name TEXT,
            vehicle_model TEXT,
            status TEXT DEFAULT 'STOLEN'
        )
    """)
    
    # Detection Audit Logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT NOT NULL,
            scan_time TEXT NOT NULL,
            status TEXT NOT NULL,
            confidence REAL
        )
    """)
    
    # Initial Sample Data
    sample_data = [
        ('ICT789', 'Ali Ahmed', 'Toyota Corolla'),
        ('LEB1234', 'Usman Khan', 'Honda Civic'),
        ('RI123', 'Zain Malik', 'Suzuki Alto'),
        ('ABC456', 'Hamza Tariq', 'Kia Sportage')
    ]
    
    for plate, owner, model in sample_data:
        try:
            cursor.execute(
                "INSERT INTO stolen_vehicles (plate_number, owner_name, vehicle_model) VALUES (?, ?, ?)",
                (plate, owner, model)
            )
        except sqlite3.IntegrityError:
            pass
            
    conn.commit()
    conn.close()

def check_stolen_status(plate_number):
    conn = sqlite3.connect("stolen_vehicles.db")
    cursor = conn.cursor()
    cursor.execute("SELECT owner_name, vehicle_model, status FROM stolen_vehicles WHERE plate_number = ?", (plate_number,))
    record = cursor.fetchone()
    conn.close()
    return record

def log_detection(plate_number, status, confidence):
    conn = sqlite3.connect("stolen_vehicles.db")
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO detection_logs (plate_number, scan_time, status, confidence) VALUES (?, ?, ?, ?)",
        (plate_number, now_str, status, confidence)
    )
    conn.commit()
    conn.close()

def add_stolen_vehicle(plate, owner, model):
    conn = sqlite3.connect("stolen_vehicles.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO stolen_vehicles (plate_number, owner_name, vehicle_model) VALUES (?, ?, ?)",
            (plate.upper(), owner, model)
        )
        conn.commit()
        conn.close()
        return True, "✅ Vehicle added to Stolen Registry successfully!"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "⚠️ Vehicle plate number already exists in database!"

def remove_stolen_vehicle(plate):
    conn = sqlite3.connect("stolen_vehicles.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stolen_vehicles WHERE plate_number = ?", (plate.upper(),))
    conn.commit()
    conn.close()
    return "✅ Vehicle record removed successfully!"

if __name__ == "__main__":
    init_db()