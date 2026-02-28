import pytest
import os
import tempfile
import sqlite3
from app.infrastructure.database.repository import ProjectRepository
from app.domain.models import Project, ProjectNode, NodeSpanConfig

@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    # Initialize schema
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE project_nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        pole_id INTEGER,
        label TEXT,
        pos_x REAL,
        pos_y REAL,
        effort_dan REAL,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE node_span_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_node_id INTEGER,
        target_node_id INTEGER,
        mt_conductor_id INTEGER,
        mt_sag_m REAL,
        bt_conductor_id INTEGER,
        bt_sag_m REAL,
        span_length_m REAL,
        angle_deg REAL,
        FOREIGN KEY(source_node_id) REFERENCES project_nodes(id),
        FOREIGN KEY(target_node_id) REFERENCES project_nodes(id)
    )
    """)
    conn.commit()
    conn.close()
    
    yield path
    try:
        os.remove(path)
    except PermissionError:
        pass

def test_database_crud_relational(db_path):
    repo = ProjectRepository(db_path)
    
    # 1. Create Project
    p = Project(name="Test Half-way BIM Project")
    created_p = repo.create_project(p)
    assert created_p.id is not None
    
    # 2. Read Projects
    projects = repo.get_projects()
    assert len(projects) == 1
    fetched_p = repo.get_project(created_p.id)
    assert fetched_p.name == "Test Half-way BIM Project"
    
    # 3. Add Project Nodes (Poles with Catalog FK)
    n1 = ProjectNode(project_id=created_p.id, pole_id=1, label="P1", pos_x=0.0, pos_y=0.0)
    n2 = ProjectNode(project_id=created_p.id, pole_id=2, label="P2", pos_x=50.0, pos_y=0.0)
    
    repo.add_node(n1)
    repo.add_node(n2)
    
    nodes = repo.get_project_nodes(created_p.id)
    assert len(nodes) == 2
    
    # Update effort
    repo.update_node_effort(nodes[0].id, 150.5)
    nodes_updated = repo.get_project_nodes(created_p.id)
    assert nodes_updated[0].effort_dan == 150.5
    
    # 4. Add Node Span Config (Edges with Conductor Catalog FKs)
    span = NodeSpanConfig(
        source_node_id=nodes[0].id,
        target_node_id=nodes[1].id,
        mt_conductor_id=1,
        mt_sag_m=0.5,
        bt_conductor_id=2,
        bt_sag_m=0.6,
        span_length_m=50.0,
        angle_deg=90.0
    )
    created_span = repo.add_span_config(span)
    assert created_span.id is not None
    
    spans = repo.get_span_configs_for_project(created_p.id)
    assert len(spans) == 1
    assert spans[0].span_length_m == 50.0
