
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_repository
from app.domain.models import NodeSpanConfig as DomainNodeSpanConfig
from app.domain.models import Project as DomainProject
from app.domain.models import ProjectNode as DomainProjectNode
from app.infrastructure.database.repository import ProjectRepository
from app.schemas.projects import (
    NodePositionUpdate,
    NodeSpanCreate,
    NodeSpanResponse,
    ProjectCreate,
    ProjectNodeCreate,
    ProjectNodeResponse,
    ProjectResponse,
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
