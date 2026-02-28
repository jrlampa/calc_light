import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
default_db_path = os.path.join(BASE_DIR, "database", "cacl_light.db")

db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("sqlite:///"):
    DB_PATH = db_url.replace("sqlite:///", "")
else:
    DB_PATH = default_db_path

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
