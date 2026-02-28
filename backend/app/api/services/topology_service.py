import sqlite3
from typing import Dict, List
from app.infrastructure.database.repository import ProjectRepository
from app.domain.models import Conductor
from app.domain.topology_service import build_topology_diagram
from app.schemas.topology import TopologyResponse

class TopologyService:
    def __init__(self, db: sqlite3.Connection, repo: ProjectRepository):
        self.db = db
        self.repo = repo

    def generate_project_topology(self, project_id: int) -> TopologyResponse:
        nodes = self.repo.get_project_nodes(project_id)
        spans = self.repo.get_span_configs_for_project(project_id)
        
        # Obter dicionário de condutores do DB
        c_rows = self.db.execute("SELECT * FROM conductors").fetchall()
        conductors_dict = {row["id"]: Conductor(**dict(row)) for row in c_rows}
        
        # Obter dicionário de postes do DB (apenas alturas por enquanto)
        p_rows = self.db.execute("SELECT * FROM poles").fetchall()
        poles_dict = {row["id"]: float(row["height_m"]) for row in p_rows}
        
        # Domain Engine: gera o layout visual
        topology = build_topology_diagram(nodes, spans, conductors_dict, poles_dict)
        
        # Atualiza banco com esforços calculados (simulando persistência assíncrona/imediata)
        for db_node in nodes:
            self.repo.update_node_effort(db_node.id, db_node.effort_dan)
            
        # Retorna o dict conforme nosso Schema 
        return TopologyResponse(
            nodes=[n.model_dump() for n in topology.nodes], 
            edges=[e.model_dump() for e in topology.edges]
        )
