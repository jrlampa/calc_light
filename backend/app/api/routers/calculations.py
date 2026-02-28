from fastapi import APIRouter
from typing import List
from app.domain.models import CalculationInput, CalculationResult, Conductor
from app.domain.calculators import calculate_level_resultant

router = APIRouter(prefix="/calculate", tags=["Calculations"])

@router.post("/", response_model=CalculationResult)
def perform_calculation(inputs: List[CalculationInput], conductors: List[Conductor]):
    """
    Receives an array of calculation inputs for different phases/levels and computes resultants.
    """
    return calculate_level_resultant(inputs=inputs, conductors=conductors)
