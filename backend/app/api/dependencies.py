import sqlite3
from collections.abc import Generator

from app.infrastructure.database.database import DB_PATH, get_db_connection
from app.infrastructure.database.repository import ProjectRepository


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

def get_repository() -> ProjectRepository:
    return ProjectRepository(db_path=DB_PATH)
