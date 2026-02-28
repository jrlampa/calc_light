from fastapi import APIRouter, Depends, HTTPException
import sqlite3
from app.api.dependencies import get_db, get_repository
from app.infrastructure.database.repository import ProjectRepository
from app.api.services.topology_service import TopologyService
from app.schemas.topology import TopologyResponse

router = APIRouter(prefix="/topology", tags=["Topology"])

@router.get("/project/{project_id}", response_model=TopologyResponse)
def get_project_topology(
    project_id: int, 
    db: sqlite3.Connection = Depends(get_db),
    repo: ProjectRepository = Depends(get_repository)
):
    service = TopologyService(db=db, repo=repo)
    return service.generate_project_topology(project_id)
