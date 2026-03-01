"""
conftest.py — configuração global para testes de integração.

Define um banco de dados SQLite temporário para cada sessão de testes,
garantindo isolamento completo e sem dependência de dados pré-existentes.
"""
import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def test_database(tmp_path_factory):
    """Cria um banco de dados SQLite temporário para a sessão de testes.

    Sobreescreve DATABASE_URL antes de importar a app para garantir que
    o ProjectRepository aponte para o DB de testes, não o de produção.
    """
    db_dir = tmp_path_factory.mktemp("db")
    db_path = str(db_dir / "test_cacl_light.db")

    # Deve ser definido ANTES de importar a app para que o módulo database.py
    # capture o valor correto ao inicializar DB_PATH.
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    # Importar e inicializar a app (cria tabelas via _apply_migrations)
    from app.main import app  # noqa: F401 — garante inicialização
    from app.infrastructure.database.database import get_db_connection

    # Garantir que o schema está criado executando uma conexão inicial
    conn = get_db_connection()

    # Seed mínimo: tabela projects deve ter a estrutura correta
    # A migration já cria tudo necessário via _apply_migrations()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            enable_equipment_drag INTEGER DEFAULT 0,
            canvas_state TEXT DEFAULT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            pole_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            pos_x REAL DEFAULT 0,
            pos_y REAL DEFAULT 0,
            effort_dan REAL DEFAULT 0,
            is_ghost INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS node_span_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_node_id INTEGER NOT NULL,
            target_node_id INTEGER NOT NULL,
            mt_conductor_id INTEGER,
            mt_sag_m REAL DEFAULT 0,
            bt_conductor_id INTEGER,
            bt_sag_m REAL DEFAULT 0,
            span_length_m REAL DEFAULT 0,
            angle_deg REAL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS poles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT NOT NULL,
            height_m REAL NOT NULL,
            resistance_dan REAL NOT NULL,
            weight_parameter_x REAL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

    yield db_path

    # Limpeza automática via tmp_path_factory
    del os.environ["DATABASE_URL"]
