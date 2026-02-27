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
