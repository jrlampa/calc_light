import pytest
import math
from light_cqt_core import LightElectricalEngine

@pytest.fixture
def engine():
    return LightElectricalEngine(catalog_path=".")

def test_vazio_absoluto(engine):
    """Cenário 1: Zero Load & Zero Distance"""
    payload = {
        "u_nominal": 127,
        "leitura_trafo": 0,
        "trafo_nominal_kva": 112.5,
        "lado_1": [
            {"id": "P-RAIZ", "condutor": "240 Cu", "comprimento": 0, "fases": 3, "ramais": []}
        ],
        "lado_2": []
    }
    # Não deve lançar ZeroDivisionError
    res = engine.processar_calculo_rede(payload)
    p0 = res["lado_1"][0]
    # Com leitura zero, a queda total (Primário + Trafo + Linha) deve ser 0.0
    assert p0["dv_acum_perc"] == 0.0
    assert p0["v_final"] == 127.0

def test_curto_circuito_infinito(engine):
    """Cenário 2: Distância Absurda (50km)"""
    # 50km de 70 Al - MX (Z ~ 0.49) carregado
    # dV% = 100 * 0.49 * 50 / 484 * 1.0 (Trifásico) ~ 500%
    dv = engine.calcular_cqt_trecho(carga_acum=100, condutor="70 Al - MX", comprimento=50000, num_fases=3)
    assert dv > 100
    
    payload = {
        "u_nominal": 127,
        "leitura_trafo": 266, # Muita carga
        "lado_1": [
            {"id": "P-LONGE", "condutor": "70 Al - MX", "comprimento": 50000, "fases": 3, "ramais": [{"tipo": "33 AA", "qtd": 10}]}
        ],
        "lado_2": []
    }
    res = engine.processar_calculo_rede(payload)
    v_final = res["lado_1"][0]["v_final"]
    # A física não permite tensão negativa
    assert v_final >= 0

def test_rateio_assombroso(engine):
    """Cenário 3: Soma de Pesos = 0 (Nenhum ramal)"""
    payload = {
        "u_nominal": 127,
        "leitura_trafo": 100,
        "lado_1": [{"id": "P1", "condutor": "33 AA", "comprimento": 10, "fases": 3, "ramais": []}],
        "lado_2": []
    }
    # Deve tratar o rateio sem crash
    res = engine.processar_calculo_rede(payload)
    assert res["lado_1"][0]["carga_kva"] == 0

def test_quebra_diversificacao(engine):
    """Cenário 4: Clientes Negativos ou Exorbitantes"""
    # Clientes negativos deve dar erro
    with pytest.raises(ValueError, match="Número de clientes não pode ser negativo"):
        engine.calcular_demanda_agregada(-5)
    
    # 1 Milhão de clientes deve travar no plateau 83.00
    demanda = engine.calcular_demanda_agregada(1_000_000)
    assert demanda == pytest.approx(2.22 * 83.00, abs=0.01)

def test_catalogo_inexistente(engine):
    """Cenário 5: Cabo Fantasma"""
    # Deve dar um erro customizado ou claro, não KeyError
    from light_cqt_core import CableNotFoundError
    with pytest.raises(CableNotFoundError):
        engine.calcular_cqt_trecho(10, "FIO_DE_BARBANTE", 100, 3)

if __name__ == "__main__":
    pytest.main([__file__])
