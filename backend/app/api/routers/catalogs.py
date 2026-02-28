from fastapi import APIRouter, Depends
import sqlite3
from typing import List
from app.api.dependencies import get_db
from app.schemas.catalogs import ConductorResponse, PoleResponse

router = APIRouter(prefix="/catalogs", tags=["Catalogs"])

@router.get("/conductors", response_model=List[ConductorResponse])
def get_conductors(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM conductors").fetchall()
    return [dict(row) for row in rows]

@router.get("/poles", response_model=List[PoleResponse])
def get_poles(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM poles").fetchall()
    return [dict(row) for row in rows]
