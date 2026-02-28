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
