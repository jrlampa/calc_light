
from pydantic import BaseModel


class ConductorResponse(BaseModel):
    id: int
    name: str
    diameter_m: float
    weight_kg_m: float
    cable_qty: int
    network_type: str
    messenger_weight: float = 0.0
    messenger_diameter: float = 0.0

class PoleResponse(BaseModel):
    id: int
    type_name: str
    height_m: float
    resistance_dan: float
    weight_parameter_x: float = 0.0


class CatalogEquipmentResponse(BaseModel):
    """Equipamento do catálogo estático para arrasto adicional (Fase 19)."""
    id: int
    name: str
    area_arrasto_m2: float
