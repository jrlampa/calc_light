
from pydantic import BaseModel, field_validator


class ProjectBase(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_be_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("O nome do projeto não pode ser vazio.")
        if len(v) > 200:
            raise ValueError("O nome do projeto não pode ultrapassar 200 caracteres.")
        return v


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: int
    created_at: str | None = None
    updated_at: str | None = None
    enable_equipment_drag: bool = False
    canvas_state: dict | None = None


class ProjectNodeBase(BaseModel):
    project_id: int
    pole_id: int
    label: str
    pos_x: float = 0.0
    pos_y: float = 0.0
    effort_dan: float = 0.0
    is_ghost: bool = False

    @field_validator("label")
    @classmethod
    def label_must_be_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("O label do poste não pode ser vazio.")
        if len(v) > 200:
            raise ValueError("O label não pode ultrapassar 200 caracteres.")
        return v


class ProjectNodeCreate(ProjectNodeBase):
    pass


class ProjectNodeResponse(ProjectNodeBase):
    id: int


class NodeSpanConfigBase(BaseModel):
    source_node_id: int
    target_node_id: int
    mt_conductor_id: int | None = None
    mt_sag_m: float = 0.0
    bt_conductor_id: int | None = None
    bt_sag_m: float = 0.0
    span_length_m: float = 0.0
    angle_deg: float = 0.0

    @field_validator("span_length_m")
    @classmethod
    def span_length_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("O comprimento do vão não pode ser negativo.")
        return v

    @field_validator("angle_deg")
    @classmethod
    def angle_must_be_in_range(cls, v: float) -> float:
        if not (-360.0 <= v <= 360.0):
            raise ValueError("O ângulo de deflexão deve estar entre -360° e 360°.")
        return v


class NodeSpanCreate(NodeSpanConfigBase):
    pass


class NodeSpanResponse(NodeSpanConfigBase):
    id: int


class NodePositionUpdate(BaseModel):
    """Payload enviado pelo React Flow ao soltar um nó (drag-and-drop)."""
    pos_x: float
    pos_y: float


class NodeGhostUpdate(BaseModel):
    """Payload para alternar a flag is_ghost de um nó."""
    is_ghost: bool


class ProjectSettingsUpdate(BaseModel):
    """Payload para atualizar as configurações globais do projeto (Fase 19)."""
    enable_equipment_drag: bool


class NodeEquipmentUpdate(BaseModel):
    """Payload para substituir os equipamentos acoplados a um nó (Fase 19)."""
    equipment_ids: list[int]


# ── Canvas Persistence (Fase 23) ────────────────────────────────────────

class CanvasStateSave(BaseModel):
    """Payload enviado pelo frontend para guardar o estado do React Flow."""
    nodes: list[dict]
    edges: list[dict]
    viewport: dict | None = None

    class Config:
        extra = "allow"


class CanvasStateResponse(BaseModel):
    """Retorno do GET canvas: inclui o canvas_state e metadados do projeto."""
    project_id: int
    has_canvas: bool
    nodes: list[dict]
    edges: list[dict]
    viewport: dict | None = None
    saved_at: str | None = None
