
from fastapi import APIRouter

from app.domain.calculators import calculate_level_resultant
from app.domain.models import CalculationInput, CalculationResult, Conductor

router = APIRouter(prefix="/calculate", tags=["Calculations"])

@router.post("/", response_model=CalculationResult)
def perform_calculation(inputs: list[CalculationInput], conductors: list[Conductor]):
    """
    Receives an array of calculation inputs for different phases/levels and computes resultants.
    """
    return calculate_level_resultant(inputs=inputs, conductors=conductors)
