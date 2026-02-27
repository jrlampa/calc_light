import sqlite3
import re
import os

db_path = "cacl_light.db"
dump_path = r"c:\CALC_LIGHT\excel_dump.txt"

def parse_val(s):
    if s.startswith("val=["):
        # extract value inside val=[...]
        m = re.search(r"val=\[([^\]]+)\]", s)
        if m:
            val_str = m.group(1)
            try:
                return float(val_str)
            except ValueError:
                return 0.0
    try:
        return float(s)
    except Exception:
        return s

def seed_db():
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
    
    # Novas tabelas para o CRUD de Projetos (Fase 2)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS project_nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        pole_id INTEGER,
        label TEXT,
        pos_x REAL DEFAULT 0.0,
        pos_y REAL DEFAULT 0.0,
        effort_dan REAL DEFAULT 0.0,
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY(pole_id) REFERENCES poles(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS node_span_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_node_id INTEGER,
        target_node_id INTEGER,
        mt_conductor_id INTEGER,
        mt_sag_m REAL DEFAULT 0.0,
        bt_conductor_id INTEGER,
        bt_sag_m REAL DEFAULT 0.0,
        span_length_m REAL DEFAULT 0.0,
        angle_deg REAL DEFAULT 0.0,
        FOREIGN KEY(source_node_id) REFERENCES project_nodes(id) ON DELETE CASCADE,
        FOREIGN KEY(target_node_id) REFERENCES project_nodes(id) ON DELETE CASCADE,
        FOREIGN KEY(mt_conductor_id) REFERENCES conductors(id),
        FOREIGN KEY(bt_conductor_id) REFERENCES conductors(id)
    )
    """)
    
    # clear tables
    cursor.execute("DELETE FROM conductors")
    cursor.execute("DELETE FROM poles")

    conductors = {}
    poles = {}

    with open(dump_path, "r", encoding="utf-8") as f:
        in_plan1 = False
        current_pole_type = ""
        
        for line in f:
            line = line.strip()
            if line == "--- Sheet 'Plan1' ---":
                in_plan1 = True
                continue
            if in_plan1 and line.startswith("--- Sheet "):
                break
                
            if not in_plan1 or not line:
                continue
                
            if ":" not in line:
                continue
                
            cell, content = line.split(":", 1)
            content = content.strip()
            
            # parse row number
            m = re.match(r"([A-Z]+)(\d+)", cell)
            if not m:
                continue
            col, row = m.groups()
            row = int(row)
            
            # Conductors
            if 3 <= row <= 50:
                if row not in conductors:
                    conductors[row] = {"name": "", "diameter_m": 0.0, "weight_kg_m": 0.0, "cable_qty": 1, "network_type": "", "md": 0.0, "mw": 0.0}
                if col == "C":
                    conductors[row]["name"] = content
                elif col == "D":
                    conductors[row]["diameter_m"] = parse_val(content)
                elif col == "E":
                    conductors[row]["weight_kg_m"] = parse_val(content)
                elif col == "F":
                    v = parse_val(content)
                    if isinstance(v, (int, float)): conductors[row]["cable_qty"] = int(v)
                elif col == "N":
                    conductors[row]["network_type"] = content
                elif col == "O":
                    v = parse_val(content)
                    if isinstance(v, (int, float)): 
                        if conductors[row]["cable_qty"] == 1: # fallback if F is not set
                            conductors[row]["cable_qty"] = int(v)
            
            # Pole Types (C57, C69, C73, C77)
            if row in [57, 69, 73, 77] and col == "C":
                current_pole_type = content
                
            if 57 <= row <= 77:
                if col == "D":
                    # format: "9 m / 150 daN"
                    if row not in poles:
                        poles[row] = {"type": current_pole_type, "h": 0.0, "r": 0.0, "w": 0.0}
                    parts = content.split(" / ")
                    if len(parts) == 2:
                        poles[row]["h"] = parse_val(parts[0].replace("m", "").strip())
                        poles[row]["r"] = parse_val(parts[1].replace("daN", "").strip())
                elif col == "E":
                    if row in poles:
                        poles[row]["w"] = parse_val(content)

    # Insert Conductors
    for r, c in conductors.items():
        if c["name"] and "altura" not in c["name"].lower():
            # Add messenger logic from dump
            if "Multiplexado" in c["name"] or "Multiplexada" in c["name"] or "MTX" in c["name"] or "Armado" in c["name"] or "Compacta" in c["network_type"]:
                c["md"] = 0.0095
                c["mw"] = 0.407
                
            try:
                cursor.execute("""
                INSERT OR IGNORE INTO conductors (name, diameter_m, weight_kg_m, cable_qty, network_type, messenger_diameter, messenger_weight)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (c["name"], c["diameter_m"], c["weight_kg_m"], c["cable_qty"], c["network_type"] or "Convencional", c["md"], c["mw"]))
            except Exception as e:
                pass

    # Insert Poles
    for r, p in poles.items():
        if isinstance(p["h"], (int, float)) and p["h"] > 0:
            try:
                cursor.execute("""
                INSERT INTO poles (type_name, height_m, resistance_dan, weight_parameter_x)
                VALUES (?, ?, ?, ?)
                """, (p["type"], p["h"], p["r"], p["w"]))
            except Exception as e:
                pass

    conn.commit()
    conn.close()
    print("Database seeded with full extraction data!")

if __name__ == "__main__":
    seed_db()
