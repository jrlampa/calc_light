
from pydantic import BaseModel


class Conductor(BaseModel):
    id: int | None = None
    name: str
    diameter_m: float
    weight_kg_m: float
    cable_qty: int
    network_type: str
    messenger_weight: float = 0.0
    messenger_diameter: float = 0.0

class Pole(BaseModel):
    id: int | None = None
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
    conductor_id: int | None = None
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
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
    enable_equipment_drag: bool = False

class ProjectNodeBase(BaseModel):
    project_id: int
    pole_id: int
    label: str
    pos_x: float = 0.0
    pos_y: float = 0.0
    effort_dan: float = 0.0
    is_ghost: bool = False

class ProjectNode(ProjectNodeBase):
    id: int | None = None

class NodeSpanConfigBase(BaseModel):
    source_node_id: int
    target_node_id: int
    mt_conductor_id: int | None = None
    mt_sag_m: float = 0.0
    bt_conductor_id: int | None = None
    bt_sag_m: float = 0.0
    span_length_m: float = 0.0
    angle_deg: float = 0.0

class NodeSpanConfig(NodeSpanConfigBase):
    id: int | None = None

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
    data: dict     # { "label": str, "effort": float, "utilization_percent": float, ... }

class ProjectTopology(BaseModel):
    nodes: list[TopologyNode]
    edges: list[TopologyEdge]


# --- Catálogo de Equipamentos (Fase 19) ---

class CatalogEquipment(BaseModel):
    id: int | None = None
    name: str
    area_arrasto_m2: float
