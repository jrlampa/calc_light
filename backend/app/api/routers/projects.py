from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.dependencies import get_repository
from app.domain.excel_exporter import build_export_zip
from app.domain.models import NodeSpanConfig as DomainNodeSpanConfig
from app.domain.models import Project as DomainProject
from app.domain.models import ProjectNode as DomainProjectNode
from app.infrastructure.database.repository import ProjectRepository
from app.schemas.projects import (
    NodeEquipmentUpdate,
    NodeGhostUpdate,
    NodePositionUpdate,
    NodeSpanCreate,
    NodeSpanResponse,
    ProjectCreate,
    ProjectNodeCreate,
    ProjectNodeResponse,
    ProjectResponse,
    ProjectSettingsUpdate,
)

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/", response_model=ProjectResponse)
def create_project(project_in: ProjectCreate, repo: ProjectRepository = Depends(get_repository)):
    domain_project = DomainProject(name=project_in.name)
    created = repo.create_project(domain_project)
    return created

@router.get("/", response_model=list[ProjectResponse])
def list_projects(repo: ProjectRepository = Depends(get_repository)):
    return repo.get_projects()

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, repo: ProjectRepository = Depends(get_repository)):
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project

@router.post("/{project_id}/nodes", response_model=ProjectNodeResponse)
def add_project_node(project_id: int, node_in: ProjectNodeCreate, repo: ProjectRepository = Depends(get_repository)):
    if node_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="ID divergente da rota")
    domain_node = DomainProjectNode(**node_in.dict())
    return repo.add_node(domain_node)

@router.post("/{project_id}/edges", response_model=NodeSpanResponse)
def add_node_span(project_id: int, span_in: NodeSpanCreate, repo: ProjectRepository = Depends(get_repository)):
    domain_span = DomainNodeSpanConfig(**span_in.dict())
    return repo.add_span_config(domain_span)

@router.patch("/{project_id}/nodes/{node_id}/position", response_model=ProjectNodeResponse)
def update_node_position(
    project_id: int,
    node_id: int,
    position_in: NodePositionUpdate,
    repo: ProjectRepository = Depends(get_repository)
):
    """Persiste a posição XY após drag-and-drop no React Flow."""
    updated = repo.update_node_position(node_id, position_in.pos_x, position_in.pos_y)
    if not updated:
        raise HTTPException(status_code=404, detail="Nó não encontrado")
    return updated


@router.patch("/{project_id}/nodes/{node_id}/ghost", response_model=ProjectNodeResponse)
def set_node_ghost(
    project_id: int,
    node_id: int,
    payload: NodeGhostUpdate,
    repo: ProjectRepository = Depends(get_repository),
):
    """Alterna a flag is_ghost de um nó do projeto.

    Nós fantasmas (is_ghost=True) representam postes da rede existente
    da concessionária: exercem tração nos postes reais do projeto mas
    são excluídos da exportação Excel e da BOM.
    """
    updated = repo.set_node_ghost(node_id, payload.is_ghost)
    if not updated:
        raise HTTPException(status_code=404, detail="Nó não encontrado")
    return updated


# ── Configurações do Projeto (Fase 19) ───────────────────────────────────────

@router.patch("/{project_id}/settings", response_model=ProjectResponse)
def update_project_settings(
    project_id: int,
    payload: ProjectSettingsUpdate,
    repo: ProjectRepository = Depends(get_repository),
):
    """Atualiza as configurações globais do projeto (ex: enable_equipment_drag)."""
    updated = repo.update_project_settings(project_id, payload.enable_equipment_drag)
    if not updated:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return updated


# ── Equipamentos por Nó (Fase 19) ────────────────────────────────────────────

@router.get("/{project_id}/nodes/{node_id}/equipment", response_model=list[int])
def get_node_equipment(
    project_id: int,
    node_id: int,
    repo: ProjectRepository = Depends(get_repository),
):
    """Retorna os IDs dos equipamentos acoplados a um nó."""
    return repo.get_node_equipment_ids(node_id)


@router.put("/{project_id}/nodes/{node_id}/equipment", response_model=list[int])
def set_node_equipment(
    project_id: int,
    node_id: int,
    payload: NodeEquipmentUpdate,
    repo: ProjectRepository = Depends(get_repository),
):
    """Substitui os equipamentos acoplados a um nó (operação idempotente)."""
    return repo.set_node_equipment_ids(node_id, payload.equipment_ids)


@router.get("/{project_id}/export/excel", tags=["Export"])
def export_project_excel(project_id: int, repo: ProjectRepository = Depends(get_repository)):
    """Gera e devolve um ZIP mestre com um arquivo .xlsm por poste REAL do projeto.

    Nós fantasmas (is_ghost=True) são excluídos sumariamente da exportação.
    Lotes de até 30 arquivos são agrupados em pastas Lote_01/, Lote_02/, etc.
    """
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    all_nodes = repo.get_project_nodes(project_id)
    # Excluir nós fantasmas da exportação e da BOM (regra de negócio da Fase 16.1)
    nodes = [n for n in all_nodes if not n.is_ghost]
    if not nodes:
        raise HTTPException(status_code=400, detail="Projeto vazio, adicione postes antes de exportar")

    postes_data = []
    for idx, node in enumerate(nodes, start=1):
        pole = repo.get_pole(node.pole_id) if node.pole_id else None
        postes_data.append({
            "projeto": project.name,
            "ponto": idx,
            "tipo_poste": pole.type_name if pole else node.label,
            "modelo_poste": (
                f"{pole.height_m} m / {int(pole.resistance_dan)} daN"
                if pole else node.label
            ),
        })

    zip_bytes = build_export_zip(postes_data)
    filename = f"projeto_{project_id}_export.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
