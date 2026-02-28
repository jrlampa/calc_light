from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import das novas rotas arquitetura Fase 3
from app.api.routers import catalogs, projects, calculations, topology, forces

app = FastAPI(title="CACL_LIGHT API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registry dos Routers
app.include_router(catalogs.router)
app.include_router(projects.router)
app.include_router(calculations.router)
app.include_router(topology.router)
app.include_router(forces.router)

@app.get("/health", tags=["System"])
def health_check():
    """Health check básico para CI/CD."""
    return {"status": "ok"}

@app.get("/forces-diagram/node/{node_id}")
def get_forces_diagram(node_id: int):
    repo = get_repository()
    # Fetch all spans where this node is source or target
    conn = get_db_connection()
    c_rows = conn.execute("SELECT * FROM conductors").fetchall()
    conductors_dict = {row["id"]: Conductor(**dict(row)) for row in c_rows}
    
    # We need the pole height for this node
    node_row = conn.execute("SELECT * FROM project_nodes WHERE id = ?", (node_id,)).fetchone()
    if not node_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Node not found")
        
    pole_row = conn.execute("SELECT * FROM poles WHERE id = ?", (node_row["pole_id"],)).fetchone()
    pole_height = float(pole_row["height_m"]) if pole_row else 9.0
    
    # Get spans
    s_rows = conn.execute("SELECT * FROM node_span_configs WHERE source_node_id = ? OR target_node_id = ?", (node_id, node_id)).fetchall()
    spans = [NodeSpanConfig(**dict(row)) for row in s_rows]
    conn.close()
    
    inputs = []
    conds = []
    
    for span in spans:
        mt_cond = conductors_dict.get(span.mt_conductor_id)
        if mt_cond:
            angle = span.angle_deg if span.source_node_id == node_id else (span.angle_deg + 180) % 360
            inputs.append(CalculationInput(
                span_m=span.span_length_m, sag_m=span.mt_sag_m, angle_deg=angle,
                pole_height_m=pole_height, anchorage_height_m=8.5,
                conductor_id=mt_cond.id, level='MT1', level_order=1
            ))
            conds.append(mt_cond)
            
        bt_cond = conductors_dict.get(span.bt_conductor_id)
        if bt_cond:
            angle = span.angle_deg if span.source_node_id == node_id else (span.angle_deg + 180) % 360
            inputs.append(CalculationInput(
                span_m=span.span_length_m, sag_m=span.bt_sag_m, angle_deg=angle,
                pole_height_m=pole_height, anchorage_height_m=7.0,
                conductor_id=bt_cond.id, level='BT', level_order=3
            ))
            conds.append(bt_cond)
            
    vectors = calculate_node_force_vectors(inputs, conds)
    return {"vectors": vectors}
