import sqlite3

from fastapi import APIRouter, Depends

from app.api.dependencies import get_db
from app.schemas.catalogs import CatalogEquipmentResponse, ConductorResponse, PoleResponse

router = APIRouter(prefix="/catalogs", tags=["Catalogs"])

@router.get("/conductors", response_model=list[ConductorResponse])
def get_conductors(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM conductors").fetchall()
    return [dict(row) for row in rows]

@router.get("/poles", response_model=list[PoleResponse])
def get_poles(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM poles").fetchall()
    return [dict(row) for row in rows]

@router.get("/equipment", response_model=list[CatalogEquipmentResponse])
def get_equipment(db: sqlite3.Connection = Depends(get_db)):
    """Retorna o catálogo estático de equipamentos para arrasto adicional (Fase 19)."""
    rows = db.execute("SELECT * FROM catalog_equipment ORDER BY name").fetchall()
    return [dict(row) for row in rows]
