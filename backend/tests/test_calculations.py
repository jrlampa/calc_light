import pytest
from app.domain.models import CalculationInput, Conductor
from app.domain.services import calculate_level_resultant

def test_traction_mt1_level():
    # Test based on the "Ponto (1)" spreadsheet logic
    # Conductor: 1/0AWG-CAA, XLPE, 13,8 kV
    # Vão (Span): 52m
    # Flecha (Sag): 0.5m
    # Ângulo: 0
    # Qtd: 3
    # Diametro: 0.017m, Peso: 0.37kg/m

    c1 = Conductor(
        id=1,
        name="1/0AWG-CAA, XLPE, 13,8 kV",
        diameter_m=0.017,
        weight_kg_m=0.37,
        cable_qty=3,
        network_type="Compacta",
        messenger_diameter=0.0095,
        messenger_weight=0.407
    )
    
    c2 = Conductor(
        id=2,
        name="1/0AWG-CAA, XLPE, 13,8 kV",
        diameter_m=0.017,
        weight_kg_m=0.37,
        cable_qty=3,
        network_type="Convencional",
        messenger_diameter=0.0,
        messenger_weight=0.0
    )
    
    # Input 1 (T1) -> Angle 0
    inp1 = CalculationInput(
        span_m=52.0,
        sag_m=0.5,
        angle_deg=0.0,
        pole_height_m=9.3,
        anchorage_height_m=9.1,
        conductor_id=1,
        level="MT1",
        level_order=1
    )

    # Input 2 (T2) -> Angle 180
    inp2 = CalculationInput(
        span_m=51.0,
        sag_m=0.5,
        angle_deg=180.0,
        pole_height_m=9.3,
        anchorage_height_m=9.1,
        conductor_id=1,
        level="MT1",
        level_order=1
    )

    res = calculate_level_resultant([inp1, inp2], [c1, c2])
    
    # Spreadsheet Resultante 1º Nível should be ~308.33 daN
    assert abs(res.resultant_level_dan - 308.33) < 0.5

    # Spreadsheet Tração on pole (MT1) should be ~365.81 daN
    assert abs(res.traction_on_pole_dan - 365.81) < 0.5
