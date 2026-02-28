from pydantic import BaseModel
from typing import List, Dict

class TopologyEdge(BaseModel):
    id: str  # e.g. "e-1-2"
    source: str
    target: str
    mt_label: str
    bt_label: str

class TopologyNode(BaseModel):
    id: str
    position: Dict[str, float] # { "x": float, "y": float }
    data: Dict[str, str | float]     # { "label": str, "effort": float }

class TopologyResponse(BaseModel):
    nodes: List[TopologyNode]
    edges: List[TopologyEdge]

class ForceVectorResponse(BaseModel):
    component_x: float
    component_y: float
    magnitude_dan: float
    angle_deg: float
    level: str
