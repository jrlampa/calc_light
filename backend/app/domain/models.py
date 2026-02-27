from pydantic import BaseModel
from typing import Optional

class Conductor(BaseModel):
    id: Optional[int] = None
    name: str
    diameter_m: float
    weight_kg_m: float
    cable_qty: int
    network_type: str
    messenger_weight: float = 0.0
    messenger_diameter: float = 0.0

class Pole(BaseModel):
    id: Optional[int] = None
    type_name: str
    height_m: float
    resistance_dan: float
    weight_parameter_x: float = 0.0

class CalculationInput(BaseModel):
    span_m: float
    sag_m: float
    angle_deg: float
    pole_height_m: float
    anchorage_height_m: float
    conductor_id: Optional[int] = None
    level: str  # e.g., 'MT1', 'MT2', 'BT'
    level_order: int # e.g. 1 for MT1, 2 for MT2
    wind_pressure: float = 16.956  # default from excel (0.00471*60^2)

class CalculationResult(BaseModel):
    total_diameter_m: float
    total_weight_kg_m: float
    wind_force_x: float
    wind_force_y: float
    traction_dan: float
    comp_x: float
    comp_y: float
    resultant_level_dan: float
    resultant_angle_deg: float
    traction_on_pole_dan: float

# --- Modelos da Fase 2 (Projetos e Diagramas) ---

class ProjectBase(BaseModel):
    name: str

class Project(ProjectBase):
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ProjectNodeBase(BaseModel):
    project_id: int
    pole_id: int
    label: str
    pos_x: float = 0.0
    pos_y: float = 0.0
    effort_dan: float = 0.0

class ProjectNode(ProjectNodeBase):
    id: Optional[int] = None

class NodeSpanConfigBase(BaseModel):
    source_node_id: int
    target_node_id: int
    mt_conductor_id: Optional[int] = None
    mt_sag_m: float = 0.0
    bt_conductor_id: Optional[int] = None
    bt_sag_m: float = 0.0
    span_length_m: float = 0.0
    angle_deg: float = 0.0

class NodeSpanConfig(NodeSpanConfigBase):
    id: Optional[int] = None

# Retorno de Topologia Híbrida (Grafo)
class TopologyEdge(BaseModel):
    id: str  # e.g. "e-1-2"
    source: str
    target: str
    mt_label: str
    bt_label: str

class TopologyNode(BaseModel):
    id: str
    position: dict # { "x": float, "y": float }
    data: dict     # { "label": str, "effort": float }

class ProjectTopology(BaseModel):
    nodes: list[TopologyNode]
    edges: list[TopologyEdge]
