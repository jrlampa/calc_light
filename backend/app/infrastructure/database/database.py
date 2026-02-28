import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
default_db_path = os.path.join(BASE_DIR, "database", "cacl_light.db")

db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("sqlite:///"):
    DB_PATH = db_url.replace("sqlite:///", "")
else:
    DB_PATH = default_db_path


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Aplica migrações incrementais de schema.

    Cada migração é idempotente: erros de 'duplicate column' são silenciados.
    Adicione novas colunas aqui em vez de recriar o banco.
    """
    migrations = [
        # Fase 16.1 — Nó Fantasma (Ghost Node)
        "ALTER TABLE project_nodes ADD COLUMN is_ghost INTEGER DEFAULT 0",
        # Fase 19 — Catálogo de Equipamentos e Arrasto Adicional
        "ALTER TABLE projects ADD COLUMN enable_equipment_drag INTEGER DEFAULT 0",
        """CREATE TABLE IF NOT EXISTS catalog_equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            area_arrasto_m2 REAL NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS node_equipment (
            node_id INTEGER NOT NULL,
            equipment_id INTEGER NOT NULL,
            PRIMARY KEY (node_id, equipment_id),
            FOREIGN KEY(node_id) REFERENCES project_nodes(id) ON DELETE CASCADE,
            FOREIGN KEY(equipment_id) REFERENCES catalog_equipment(id) ON DELETE CASCADE
        )""",
        # Seed do catálogo estático de equipamentos (idempotente via INSERT OR IGNORE)
        "INSERT OR IGNORE INTO catalog_equipment (name, area_arrasto_m2) VALUES ('Trafo 45 kVA', 0.85)",
        "INSERT OR IGNORE INTO catalog_equipment (name, area_arrasto_m2) VALUES ('Trafo 75 kVA', 1.05)",
        "INSERT OR IGNORE INTO catalog_equipment (name, area_arrasto_m2) VALUES ('Trafo 112,5 kVA', 1.25)",
        "INSERT OR IGNORE INTO catalog_equipment (name, area_arrasto_m2) VALUES ('Cruzeta Polimérica 2,0 m', 0.30)",
        "INSERT OR IGNORE INTO catalog_equipment (name, area_arrasto_m2) VALUES ('Cruzeta Metálica 2,4 m', 0.40)",
        "INSERT OR IGNORE INTO catalog_equipment (name, area_arrasto_m2) VALUES ('Chave Faca MT', 0.15)",
        "INSERT OR IGNORE INTO catalog_equipment (name, area_arrasto_m2) VALUES ('Chave a Óleo MT', 0.20)",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # coluna já existe


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _apply_migrations(conn)
    return conn
