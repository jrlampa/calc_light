import sqlite3

db_path = "cacl_light.db"

def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conductors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        diameter_m REAL,
        weight_kg_m REAL,
        cable_qty INTEGER,
        network_type TEXT,
        messenger_diameter REAL DEFAULT 0.0,
        messenger_weight REAL DEFAULT 0.0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS poles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_name TEXT,
        height_m REAL,
        resistance_dan REAL,
        weight_parameter_x REAL DEFAULT 0.0
    )
    """)

    # Seed Data (Sample extracted from Plan1)
    conductors_data = [
        ("556MCM-CA, Nu", 0.022, 0.779, 3, "Compacta", 0.0, 0.0),
        ("397MCM-CA, Nu", 0.0184, 0.558, 3, "Convencional", 0.0, 0.0),
        ("1/0AWG-CAA, Nu", 0.0102, 0.217, 3, "Multiplexado", 0.0, 0.0),
        ("4 AWG-CAA, Nu", 0.0064, 0.085, 3, "Multiplexada", 0.0, 0.0),
        ("397MCM-CA, XLPE, 13,8 kV", 0.026, 0.749, 1, "Armado", 0.0, 0.0),
        ("1/0AWG-CAA, XLPE, 13,8 kV", 0.017, 0.37, 3, "Compacta", 0.0095, 0.407), # Using standard messenger for 13.8 compact
    ]

    poles_data = [
        ("Concreto circular", 9.0, 150.0, 12.24),
        ("Concreto circular", 9.0, 300.0, 14.18),
        ("Concreto circular", 11.0, 300.0, 18.49),
        ("Concreto circular", 11.0, 600.0, 20.09),
        ("Concreto circular", 12.0, 600.0, 22.53),
        ("Concreto duplo T", 11.0, 600.0, 28.78),
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO conductors (name, diameter_m, weight_kg_m, cable_qty, network_type, messenger_diameter, messenger_weight)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, conductors_data)

    cursor.executemany("""
    INSERT OR IGNORE INTO poles (type_name, height_m, resistance_dan, weight_parameter_x)
    VALUES (?, ?, ?, ?)
    """, poles_data)

    conn.commit()
    conn.close()
    print("Database initialized and seeded.")

if __name__ == "__main__":
    init_db()
