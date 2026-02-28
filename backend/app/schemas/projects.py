from pydantic import BaseModel
from typing import Optional, List

class ProjectBase(BaseModel):
    name: str

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ProjectNodeBase(BaseModel):
    project_id: int
    pole_id: int
    label: str
    pos_x: float = 0.0
    pos_y: float = 0.0
    effort_dan: float = 0.0

class ProjectNodeCreate(ProjectNodeBase):
    pass

class ProjectNodeResponse(ProjectNodeBase):
    id: int

class NodeSpanConfigBase(BaseModel):
    source_node_id: int
    target_node_id: int
    mt_conductor_id: Optional[int] = None
    mt_sag_m: float = 0.0
    bt_conductor_id: Optional[int] = None
    bt_sag_m: float = 0.0
    span_length_m: float = 0.0
    angle_deg: float = 0.0

class NodeSpanCreate(NodeSpanConfigBase):
    pass

class NodeSpanResponse(NodeSpanConfigBase):
    id: int
