import pytest
from app.domain.electrical_services import LightElectricalService
from app.domain.electrical_models import CqtInputSchema, RamalSchema, PosteSchema
from app.domain.exceptions import CableNotFoundError

@pytest.fixture
def service():
    return LightElectricalService()

def test_service_calc_full_no_load(service):
    # Com 0 carga, v_final deve ser igual u_nominal (127) e status Ok
    payload = CqtInputSchema(
        u_nominal=127.0,
        leitura_trafo=0.0,
        trafo_nominal_kva=300.0,
        lado_1=[
            PosteSchema(
                id="P1",
                condutor="33 AA",
                comprimento=1.0,
                fases=3,
                ramais=[]
            )
        ],
        lado_2=[]
    )
    result = service.calcular_cqt_completo(payload)
    assert result.lado_1[0].v_final == 127.0
    assert result.lado_1[0].status == "Ok"

def test_hygiene_invalid_input(service):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        RamalSchema(tipo="Cabo", qtd=-1)

def test_hygiene_negative_clients(service):
    with pytest.raises(ValueError, match="não pode ser negativo"):
        service.calcular_demanda_agregada(-10)

def test_hygiene_cable_not_found(service):
    with pytest.raises(CableNotFoundError):
        service.calcular_cqt_trecho(10.0, "CABO_FANTASMA", 100.0, 3)

def test_clamping_negative_voltage(service):
    payload = CqtInputSchema(
        u_nominal=127.0,
        leitura_trafo=1000.0,
        lado_1=[PosteSchema(
            id="LONGE", 
            condutor="33 AA", 
            comprimento=500000.0, 
            fases=3,
            ramais=[RamalSchema(tipo="33 AA", qtd=100)]
        )],
        lado_2=[]
    )
    res = service.calcular_cqt_completo(payload)
    assert res.lado_1[0].v_final == 0.0

def test_rateio_sem_ramais(service):
    payload = CqtInputSchema(
        u_nominal=127.0,
        leitura_trafo=100.0,
        lado_1=[PosteSchema(id="P1", condutor="33 AA", comprimento=10.0, fases=3, ramais=[])],
        lado_2=[]
    )
    res = service.calcular_cqt_completo(payload)
    assert res.lado_1[0].carga_kva == 0.0

def test_demanda_agregada_ranges(service):
    assert service.calcular_demanda_agregada(2) == pytest.approx(2.22 * 3.88)
    assert service.calcular_demanda_agregada(300) == pytest.approx(2.22 * 83.00)
    assert service.calcular_demanda_agregada(100) > 2.22 * 3.88

def test_peso_poste_fallback(service):
    # Simula condutor que não está no catálogo principal para disparar amp_map
    peso = service.calcular_peso_poste([RamalSchema(tipo="16", qtd=1)])
    assert peso == 63.0

def test_cqt_fases_e_tipos(service):
    c1 = service.calcular_cqt_trecho(10, "33 AA", 100, 1, "rede")
    c2 = service.calcular_cqt_trecho(10, "33 AA", 100, 2, "rede")
    c3 = service.calcular_cqt_trecho(10, "33 AA", 100, 3, "rede")
    assert c1 > c2 > c3
    rl3 = service.calcular_cqt_trecho(10, "33 AA", 100, 3, "rl")
    assert rl3 == c3 * 2.0

def test_trafo_not_found_but_powers_exist(service):
    payload = CqtInputSchema(
        u_nominal=127.0,
        leitura_trafo=10.0,
        trafo_nominal_kva=400.0,
        lado_1=[PosteSchema(id="P1", condutor="33 AA", comprimento=10, fases=3, ramais=[RamalSchema(tipo="33", qtd=1)])],
        lado_2=[]
    )
    res = service.calcular_cqt_completo(payload)
    assert res.lado_1[0].v_final > 0

def test_ramal_no_id(service):
    p = PosteSchema(id="P1-RAMAL", condutor="33 AA", comprimento=10, fases=3, ramais=[RamalSchema(tipo="33 AA", qtd=1)])
    payload = CqtInputSchema(u_nominal=127, leitura_trafo=10, lado_1=[p])
    res = service.calcular_cqt_completo(payload)
    assert res.lado_1[0].dv_trecho_perc > 0

def test_load_json_edge_cases(service):
    # Testar arquivo inexistente em lugar nenhum para hit no 'return []' (linha 46)
    assert service._load_json("TRULY_NON_EXISTENT.json") == []
    
    # Testar fallback alterando temporariamente o catalog_path (linha 35)
    # Como rodamos de 'backend/', e os jsons estão no root 'C:\CALC_LIGHT', 
    # o fallback '..' deve encontrá-los.
    service_temp = LightElectricalService(catalog_path="empty_folder")
    assert len(service_temp._load_json("cables_catalog_light.json")) > 0

def test_icc_accumulation(service):
    # Testar se Icc cai com a distância
    payload = CqtInputSchema(
        u_nominal=127.0,
        leitura_trafo=10.0,
        trafo_nominal_kva=112.5,
        lado_1=[
            PosteSchema(id="P1", condutor="33 AA", comprimento=10, fases=3, ramais=[RamalSchema(tipo="33", qtd=1)]),
            PosteSchema(id="P2", condutor="33 AA", comprimento=1000, fases=3, ramais=[RamalSchema(tipo="33", qtd=1)]) # longe
        ],
        lado_2=[]
    )
    res = service.calcular_cqt_completo(payload)
    icc1 = res.lado_1[0].icc_amperes
    icc2 = res.lado_1[1].icc_amperes
    # Icc deve diminuir
    assert icc1 > icc2
    # Icc na raiz do 112.5 kVA deve ser alto (kA)
    assert icc1 > 1000

def test_complex_impedance_service(service):
    # Validar cálculo complexo com nome exato do catálogo para hit no 'else'
    z = service.calcular_impedancia_trecho("33", 1000) # 1km
    # No catálogo "33" tem R=0.3225 e X=0.2968
    assert z.real == pytest.approx(0.3225)
    assert z.imag == pytest.approx(0.2968)
    
def test_demanda_zero_clientes(service):
    # Hit na linha 66 do service
    assert service.calcular_demanda_agregada(0) == 0.0
