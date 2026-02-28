from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers modulares (Arquitetura DDD - Fase 3+)
from app.api.routers import catalogs, projects, calculations, topology, forces

app = FastAPI(
    title="CACL LIGHT API",
    description="API para cálculo de esforço mecânico em postes de distribuição (padrão Light).",
    version="0.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro dos routers — nenhuma lógica de negócio aqui (Smart Backend, DDD)
app.include_router(catalogs.router)
app.include_router(projects.router)
app.include_router(calculations.router)
app.include_router(topology.router)
app.include_router(forces.router)

@app.get("/health", tags=["System"])
def health_check():
    """Health check para CI/CD e Docker HEALTHCHECK."""
    return {"status": "ok", "version": "0.3.0"}
