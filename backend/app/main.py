from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
from pydantic import BaseModel
from pydantic import BaseModel
from typing import List
from app.domain.models import CalculationInput, CalculationResult, Conductor
from app.domain.services import calculate_level_resultant

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
