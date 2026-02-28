from fastapi.testclient import TestClient
import sqlite3
import pytest
import os
import tempfile
from app.main import app
from app.api.dependencies import get_db, get_repository
from app.infrastructure.database.repository import ProjectRepository
from app.domain.models import Project

# Mock de DB em tempfile para que o ProjectRepository possa abrir as próprias conexões
@pytest.fixture(scope="module")
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Criar schemas mínimos
    conn.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS project_nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        pole_id INTEGER,
        label TEXT,
        pos_x REAL,
        pos_y REAL,
        effort_dan REAL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS node_span_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_node_id INTEGER NOT NULL,
        target_node_id INTEGER NOT NULL,
        mt_conductor_id INTEGER,
        mt_sag_m REAL DEFAULT 0.0,
        bt_conductor_id INTEGER,
        bt_sag_m REAL DEFAULT 0.0,
        span_length_m REAL DEFAULT 0.0,
        angle_deg REAL DEFAULT 0.0
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS conductors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, diameter_m REAL, weight_kg_m REAL, cable_qty INTEGER, network_type TEXT,
        messenger_weight REAL, messenger_diameter REAL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS poles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_name TEXT, height_m REAL, resistance_dan REAL, weight_parameter_x REAL
    )''')
    
    # Inserir mocks
    conn.execute("INSERT INTO conductors (name, diameter_m, weight_kg_m, cable_qty, network_type, messenger_weight, messenger_diameter) VALUES ('Mock MT', 0.015, 0.5, 3, 'MT', 0.0, 0.0)")
    conn.execute("INSERT INTO poles (type_name, height_m, resistance_dan, weight_parameter_x) VALUES ('DT-1000', 11, 1000, 0.0)")
    conn.commit()
    conn.close()
    
    yield path
    
    try:
        os.remove(path)
    except PermissionError:
        pass

@pytest.fixture(scope="module")
def client(temp_db_path):
    def override_get_db():
        conn = sqlite3.connect(temp_db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def override_get_repo():
        return ProjectRepository(db_path=temp_db_path)
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_repository] = override_get_repo
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_get_catalogs(client):
    response_poles = client.get("/catalogs/poles")
    assert response_poles.status_code == 200
    assert len(response_poles.json()) > 0
    
    response_cond = client.get("/catalogs/conductors")
    assert response_cond.status_code == 200
    assert len(response_cond.json()) > 0

def test_create_and_get_project(client):
    payload = {"name": "Projeto Teste Pydantic"}
    res_post = client.post("/projects/", json=payload)
    assert res_post.status_code == 200
    proj = res_post.json()
    assert proj["name"] == "Projeto Teste Pydantic"
    assert "id" in proj
    
    p_id = proj["id"]
    p_id = proj["id"]
    res_get = client.get(f"/projects/{p_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == p_id

def test_create_topology_and_forces(client):
    # 1. Obter catálogo de condutor para amarrar nos spans
    cond_res = client.get("/catalogs/conductors")
    cond_id = cond_res.json()[0]["id"]
    
    # 2. Criar um novo projeto
    proj_res = client.post("/projects/", json={"name": "Projeto Engine Test"})
    p_id = proj_res.json()["id"]
    
    # 3. Criar Node 1 e Node 2
    n1_payload = {"project_id": p_id, "pole_id": 1, "label": "Poste A", "pos_x": 0, "pos_y": 0}
    n2_payload = {"project_id": p_id, "pole_id": 1, "label": "Poste B", "pos_x": 50, "pos_y": 0}
    
    n1_id = client.post(f"/projects/{p_id}/nodes", json=n1_payload).json()["id"]
    n2_id = client.post(f"/projects/{p_id}/nodes", json=n2_payload).json()["id"]
    
    # 4. Criar um Vão (Span) entre 1 e 2
    span_payload = {
        "source_node_id": n1_id,
        "target_node_id": n2_id,
        "mt_conductor_id": cond_id,
        "mt_sag_m": 0.5,
        "span_length_m": 50.0,
        "angle_deg": 180.0
    }
    span_res = client.post(f"/projects/{p_id}/edges", json=span_payload)
    assert span_res.status_code == 200
    
    # 5. Testar Topologia
    top_res = client.get(f"/topology/project/{p_id}")
    assert top_res.status_code == 200
    top_data = top_res.json()
    assert "nodes" in top_data and "edges" in top_data
    assert len(top_data["nodes"]) == 2
    assert len(top_data["edges"]) == 1
    
    # 6. Testar Forces Diagram (Vetores do Nó 1)
    force_res = client.get(f"/forces-diagram/node/{n1_id}")
    assert force_res.status_code == 200
    forces = force_res.json()
    assert len(forces) > 0
    assert "magnitude_dan" in forces[0]

