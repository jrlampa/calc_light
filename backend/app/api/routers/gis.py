"""Rotas GIS: parsing de arquivos geoespaciais e importação atômica de nós.

Endpoints:
- POST /projects/{id}/parse-file        → lista de pontos extraídos
- POST /projects/{id}/import-nodes      → importação atômica de nós selecionados
- GET  /projects/{id}/nodes/{nid}/outgoing-conductors → herança de condutores
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.dependencies import get_repository
from app.domain.gis_parser import parse_file
from app.domain.models import ProjectNode
from app.infrastructure.database.repository import ProjectRepository
from app.schemas.gis import (
    ImportNodesRequest,
    OutgoingConductorsResponse,
    ParsedPointResponse,
)

router = APIRouter(prefix="/projects", tags=["GIS"])

# Espaçamento entre nós importados no canvas (pixels)
_GRID_COLS = 10
_GRID_SPACING = 150
_GRID_OFFSET_X = 500


@router.post("/{project_id}/parse-file", response_model=list[ParsedPointResponse])
async def parse_project_file(
    project_id: int,
    file: UploadFile,
    repo: ProjectRepository = Depends(get_repository),
) -> list[ParsedPointResponse]:
    """Parseia um arquivo geoespacial (.kml, .kmz, .geojson, .xlsx) e devolve os pontos.

    Retorna HTTP 400 com mensagem amigável para arquivos malformados ou extensões inválidas.
    """
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    content = await file.read()
    try:
        points = parse_file(file.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return [ParsedPointResponse(label=p.label, lat=p.lat, lng=p.lng) for p in points]


@router.post("/{project_id}/import-nodes", response_model=list[dict])
def import_project_nodes(
    project_id: int,
    body: ImportNodesRequest,
    repo: ProjectRepository = Depends(get_repository),
) -> list[dict]:
    """Importa atomicamente uma lista de pontos GIS como nós do projeto.

    Posiciona os nós em uma grade no canvas (pos_x/pos_y).
    pole_id=0 indica nó sem poste do catálogo atribuído.
    """
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    if not body.points:
        raise HTTPException(status_code=400, detail="Nenhum ponto selecionado para importar")

    nodes_to_insert = [
        ProjectNode(
            project_id=project_id,
            pole_id=0,
            label=pt.label,
            pos_x=float((i % _GRID_COLS) * _GRID_SPACING + _GRID_OFFSET_X),
            pos_y=float((i // _GRID_COLS) * _GRID_SPACING),
            effort_dan=0.0,
        )
        for i, pt in enumerate(body.points)
    ]

    try:
        created = repo.import_nodes_atomic(nodes_to_insert)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha na importação atômica: {exc}") from exc

    return [{"id": n.id, "label": n.label, "pos_x": n.pos_x, "pos_y": n.pos_y} for n in created]


@router.get(
    "/{project_id}/nodes/{node_id}/outgoing-conductors",
    response_model=OutgoingConductorsResponse,
)
def get_outgoing_conductors(
    project_id: int,
    node_id: int,
    repo: ProjectRepository = Depends(get_repository),
) -> OutgoingConductorsResponse:
    """Retorna os condutores do vão de saída mais recente do nó.

    Usado pelo frontend para aplicar a Lógica de Herança de Condutores ao
    criar uma nova aresta a partir de um nó que já possui cabos configurados.
    Se o nó não possui vão de saída, retorna zeros/nulos (sem herança).
    """
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    span = repo.get_outgoing_span_config(node_id)
    if span is None:
        return OutgoingConductorsResponse()

    return OutgoingConductorsResponse(
        mt_conductor_id=span.mt_conductor_id,
        mt_sag_m=span.mt_sag_m,
        bt_conductor_id=span.bt_conductor_id,
        bt_sag_m=span.bt_sag_m,
    )
