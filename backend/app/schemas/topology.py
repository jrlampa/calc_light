
from pydantic import BaseModel


class TopologyEdge(BaseModel):
    id: str  # e.g. "e-1-2"
    source: str
    target: str
    mt_label: str
    bt_label: str

class TopologyNode(BaseModel):
    id: str
    position: dict[str, float] # { "x": float, "y": float }
    data: dict[str, str | float | bool]  # { "label": str, "effort": float, "utilization_percent": float, ... }

class TopologyResponse(BaseModel):
    nodes: list[TopologyNode]
    edges: list[TopologyEdge]

class ForceVectorResponse(BaseModel):
    component_x: float
    component_y: float
    magnitude_dan: float
    angle_deg: float
    level: str
    nominal_capacity: float | None = None  # Only present on RESULT vector
