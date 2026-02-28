import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_db, get_repository
from app.domain.models import Conductor
from app.domain.topology_service import calculate_node_force_vectors
from app.infrastructure.database.repository import ProjectRepository
from app.schemas.topology import ForceVectorResponse

router = APIRouter(prefix="/forces-diagram", tags=["Forces Diagram"])

@router.get("/node/{node_id}", response_model=list[ForceVectorResponse])
def get_node_force_vectors(
    node_id: int,
    db: sqlite3.Connection = Depends(get_db),
    repo: ProjectRepository = Depends(get_repository)
):
    # Primeiro achamos em qual projeto e informações o nó base reside
    # Para ser purista, faríamos um find_node_by_id. Vamos adicionar isso ao repo se não houver.
    # Mas como o cálculo envolve os spans, precisamos do project_id.

    # 1. Obter info básica para desvendar Project_id.
    # (Como o repository não tem get_node_by_id, vamos pegar todos os projetos e varrer, ou melhor, adicionar um find rápido)
    cursor = db.cursor()
    row = cursor.execute("SELECT project_id, pole_id FROM project_nodes WHERE id = ?", (node_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Node não encontrado")

    project_id, pole_id = row

    # 2. Re-hidratar a malha do projeto
    nodes = repo.get_project_nodes(project_id)
    spans = repo.get_span_configs_for_project(project_id)

    node_obj = next((n for n in nodes if n.id == node_id), None)
    if not node_obj:
        raise HTTPException(status_code=404, detail="Node inconsistency")

    c_rows = db.execute("SELECT * FROM conductors").fetchall()
    conductors_dict = {row["id"]: Conductor(**dict(row)) for row in c_rows}

    p_rows = db.execute("SELECT * FROM poles").fetchall()
    poles_dict = {row["id"]: float(row["height_m"]) for row in p_rows}

    # 3. Chamar a Domain Engine especializada
    vectors = calculate_node_force_vectors(node_obj, spans, conductors_dict, poles_dict)

    # Renderizar na tipagem correta
    response = []
    for vec in vectors:
        response.append(ForceVectorResponse(
            component_x=vec["component_x"],
            component_y=vec["component_y"],
            magnitude_dan=vec["magnitude_dan"],
            angle_deg=vec["angle_deg"],
            level=vec["level"]
        ))
    return response
