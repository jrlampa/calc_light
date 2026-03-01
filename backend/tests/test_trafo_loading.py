import pytest
from app.domain.electrical_services import LightElectricalService
from app.domain.electrical_models import CqtInputSchema, PosteSchema, RamalSchema


@pytest.fixture
def service():
    return LightElectricalService()


def test_master_case_trafo_loading(service):
    """
    Caso de Prova Mestre:
    Carga Atual = 85 kVA, Margem = 15%, Trafo = 100 kVA.
    Carga_Projetada = 85 / (1 - 0.15) = 85 / 0.85 = 100 kVA exatos.
    Carregamento = (100 / 100) * 100 = 100%.
    """
    # leitura_trafo * 0.375 = 85 kVA -> leitura_trafo = 85 / 0.375 = 226.667
    leitura = 85.0 / 0.375

    payload = CqtInputSchema(
        u_nominal=220.0,
        leitura_trafo=leitura,
        trafo_nominal_kva=100.0,
        growth_margin_pct=0.15,
        lado_1=[
            PosteSchema(id="P1", condutor="33 AA", comprimento=10, fases=3,
                        ramais=[RamalSchema(tipo="33", qtd=1)])
        ],
        lado_2=[]
    )
    res = service.calcular_cqt_completo(payload)

    assert res.carga_atual_kva == pytest.approx(85.0, abs=0.01)
    assert res.carga_projetada_kva == pytest.approx(100.0, abs=0.01)
    assert res.trafo_loading_percent == pytest.approx(100.0, abs=0.01)
    assert res.trafo_status == "Ok"


def test_trafo_sobrecarga(service):
    """Com margem zero e carga acima do nominal, deve retornar Sobrecarga."""
    leitura = 120.0 / 0.375  # 120 kVA > 100 kVA nomimal

    payload = CqtInputSchema(
        u_nominal=220.0,
        leitura_trafo=leitura,
        trafo_nominal_kva=100.0,
        growth_margin_pct=0.0,  # Sem margem
        lado_1=[
            PosteSchema(id="P1", condutor="33 AA", comprimento=10, fases=3,
                        ramais=[RamalSchema(tipo="33", qtd=1)])
        ],
        lado_2=[]
    )
    res = service.calcular_cqt_completo(payload)

    assert res.trafo_loading_percent > 100.0
    assert res.trafo_status == "Sobrecarga"


def test_trafo_folga_confortavel(service):
    """Com 50 kVA num trafo de 112.5 kVA e 15% de margem, deve ficar bem abaixo de 100%."""
    leitura = 50.0 / 0.375

    payload = CqtInputSchema(
        u_nominal=127.0,
        leitura_trafo=leitura,
        trafo_nominal_kva=112.5,
        growth_margin_pct=0.15,
        lado_1=[
            PosteSchema(id="P1", condutor="33", comprimento=50, fases=3,
                        ramais=[RamalSchema(tipo="33", qtd=1)])
        ],
        lado_2=[]
    )
    res = service.calcular_cqt_completo(payload)

    # carga_projetada = 50 / 0.85 = 58.82 kVA. Loading = 58.82/112.5 = 52.3%
    assert res.carga_projetada_kva == pytest.approx(58.82, abs=0.1)
    assert res.trafo_loading_percent == pytest.approx(52.3, abs=0.5)
    assert res.trafo_status == "Ok"


def test_trafo_loading_zero_load(service):
    """Com carga zero, projeção e carregamento devem ser zero."""
    payload = CqtInputSchema(
        u_nominal=127.0,
        leitura_trafo=0.0,
        trafo_nominal_kva=112.5,
        growth_margin_pct=0.15,
        lado_1=[],
        lado_2=[]
    )
    res = service.calcular_cqt_completo(payload)

    assert res.carga_atual_kva == pytest.approx(0.0)
    assert res.carga_projetada_kva == pytest.approx(0.0)
    assert res.trafo_loading_percent == pytest.approx(0.0)
    assert res.trafo_status == "Ok"
