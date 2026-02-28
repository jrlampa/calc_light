import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "backend", "database", "cacl_light.db")

def fix_db():
    if not os.path.exists(DB_PATH):
        print(f"Banco não encontrado em {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verifica tabelas e colunas
    tables = {
        "projects": ["id", "name", "created_at", "updated_at"],
        "project_nodes": ["id", "project_id", "pole_id", "label", "pos_x", "pos_y", "effort_dan"],
        "node_span_configs": ["id", "source_node_id", "target_node_id", "mt_conductor_id", "mt_sag_m", "bt_conductor_id", "bt_sag_m", "span_length_m", "angle_deg"]
    }
    
    for table, expected_cols in tables.items():
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            existing_cols = [row[1] for row in cursor.fetchall()]
            
            if not existing_cols:
                print(f"Tabela {table} não existe! Rodando seed_full.py seria melhor.")
                continue
                
            for col in expected_cols:
                if col not in existing_cols:
                    print(f"Adicionando coluna {col} na tabela {table}...")
                    # Simplificação para o fix: a maioria é REAL ou DATETIME
                    col_type = "DATETIME DEFAULT CURRENT_TIMESTAMP" if "at" in col else "REAL DEFAULT 0.0"
                    if col == "name" or col == "label": col_type = "TEXT"
                    
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except Exception as e:
            print(f"Erro ao processar {table}: {e}")

    conn.commit()
    conn.close()
    print("Correção de banco finalizada.")

if __name__ == "__main__":
    fix_db()
