from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
from pydantic import BaseModel
from typing import List, Dict

from app.domain.models import (
    CalculationInput, CalculationResult, Conductor,
    Project, ProjectNode, NodeSpanConfig, ProjectTopology
)
from app.domain.services import calculate_level_resultant
from app.domain.topology_service import build_topology_diagram, calculate_node_force_vectors
from app.domain.project_repository import ProjectRepository

app = FastAPI(title="CACL_LIGHT API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

@app.get("/conductors")
def get_conductors():
    conn = get_db_connection()
    conductors = conn.execute("SELECT * FROM conductors").fetchall()
    conn.close()
    return [dict(row) for row in conductors]

@app.get("/poles")
def get_poles():
    conn = get_db_connection()
    poles = conn.execute("SELECT * FROM poles").fetchall()
    conn.close()
    return [dict(row) for row in poles]

@app.post("/calculate", response_model=CalculationResult)
def perform_calculation(inputs: List[CalculationInput], conductors: List[Conductor]):
    """
    Receives an array of calculation inputs for different phases/levels and computes resultants.
    """
    return calculate_level_resultant(inputs=inputs, conductors=conductors)

@app.get("/health")
def health_check():
    return {"status": "ok"}

# --- Endpoints Fase 2 (CRUD Projetos e Diagramas) ---

def get_repository():
    return ProjectRepository(db_path=DB_PATH)

@app.post("/projects", response_model=Project)
def create_project(project: Project):
    return get_repository().create_project(project)

@app.get("/projects", response_model=List[Project])
def list_projects():
    return get_repository().get_projects()

@app.post("/projects/{project_id}/nodes", response_model=ProjectNode)
def add_project_node(project_id: int, node: ProjectNode):
    node.project_id = project_id
    return get_repository().add_node(node)

@app.post("/projects/{project_id}/spans", response_model=NodeSpanConfig)
def add_node_span(project_id: int, span: NodeSpanConfig):
    return get_repository().add_span_config(span)

@app.get("/topology/project/{project_id}", response_model=ProjectTopology)
def get_project_topology(project_id: int):
    repo = get_repository()
    nodes = repo.get_project_nodes(project_id)
    spans = repo.get_span_configs_for_project(project_id)
    
    # Fetch conductors as dict
    conn = get_db_connection()
    c_rows = conn.execute("SELECT * FROM conductors").fetchall()
    conductors_dict = {row["id"]: Conductor(**dict(row)) for row in c_rows}
    
    # Fetch poles as dict
    p_rows = conn.execute("SELECT * FROM poles").fetchall()
    poles_dict = {row["id"]: float(row["height_m"]) for row in p_rows}
    conn.close()
    
    # Smart Backend: Build Topology completely isolated in domain
    topology = build_topology_diagram(nodes, spans, conductors_dict, poles_dict)
    
    # Update effort back to DB asynchronously (or sync here for simplicity)
    for db_node in nodes:
        repo.update_node_effort(db_node.id, db_node.effort_dan)
        
    return topology

# Requires the exact inputs to render node vectors 2.5D
class ForceDiagramRequest(BaseModel):
    inputs: List[CalculationInput]
    conductors: List[Conductor]

@app.post("/forces-diagram/node")
def get_forces_diagram(req: ForceDiagramRequest):
    vectors = calculate_node_force_vectors(req.inputs, req.conductors)
    return {"vectors": vectors}
