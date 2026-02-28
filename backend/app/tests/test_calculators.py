from app.domain.calculators import calculate_level_resultant
from app.domain.models import CalculationInput, Conductor


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


def test_angle_edge_cases():
    c1 = Conductor(
        id=1, name="Test", diameter_m=0.01, weight_kg_m=0.1, cable_qty=1, network_type="Conv"
    )
    # Case 1: X = 0, Y = 0 (symmetric spans 0 and 180)
    inp1 = CalculationInput(span_m=50, sag_m=0.5, angle_deg=0, pole_height_m=10, anchorage_height_m=9, conductor_id=1, level="MT", level_order=1)
    inp2 = CalculationInput(span_m=50, sag_m=0.5, angle_deg=180, pole_height_m=10, anchorage_height_m=9, conductor_id=1, level="MT", level_order=1)
    res = calculate_level_resultant([inp1, inp2], [c1, c1])
    assert res.resultant_angle_deg == 0.0

    # Case 2: X = 0, Y != 0 (symmetric spans 90 and 90, meaning X will be 0 and Y > 0)
    inp3 = CalculationInput(span_m=50, sag_m=0.5, angle_deg=90, pole_height_m=10, anchorage_height_m=9, conductor_id=1, level="MT", level_order=1)
    res2 = calculate_level_resultant([inp3], [c1])
    assert res2.resultant_angle_deg > 0

    # Case 3: X < 0
    inp4 = CalculationInput(span_m=50, sag_m=0.5, angle_deg=180, pole_height_m=10, anchorage_height_m=9, conductor_id=1, level="MT", level_order=1)
    res3 = calculate_level_resultant([inp4], [c1])
    assert res3.resultant_angle_deg == 180

    # Case 4: Zero calculation without crashing (pole_h = 0)
    inp5 = CalculationInput(span_m=50, sag_m=0.5, angle_deg=0, pole_height_m=0, anchorage_height_m=9, conductor_id=1, level="MT", level_order=1)
    res4 = calculate_level_resultant([inp5], [c1])
    assert res4.traction_on_pole_dan == 0.0
