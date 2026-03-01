import pytest
import math
from app.domain.electrical_services import LightElectricalService
from app.domain.electrical_models import CqtInputSchema, PosteSchema, RamalSchema

def test_master_case_thermal():
    """
    Caso de Prova Mestre: 
    240 Cu, Ampacidade 430A, Carga 99.62 kVA @ 220V/3-fases.
    I = 99.62 / (0.22 * sqrt(3)) = 261.44A
    T = 30 + (261.44 / 430) * 60 = 66.48 -> ~ 66.5°C
    """
    service = LightElectricalService()
    
    # Injetando um poste com a carga exata do Master Case
    # Como a carga é rateada, vamos garantir que a carga no trecho seja 99.62
    # leitura_trafo * 0.375 = 99.62 -> leitura_trafo = 99.62 / 0.375 = 265.653
    carga_alvo = 99.62
    leitura_necessaria = carga_alvo / 0.375
    
    payload = CqtInputSchema(
        u_nominal=220.0,
        leitura_trafo=leitura_necessaria,
        trafo_nominal_kva=112.5,
        lado_1=[
            PosteSchema(
                id="P1", 
                condutor="240 Cu", 
                comprimento=10, 
                fases=3,
                ramais=[RamalSchema(tipo="240 Cu", qtd=1)] # Peso para o rateio
            )
        ],
        lado_2=[]
    )
    
    res = service.calcular_cqt_completo(payload)
    out_p1 = res.lado_1[0]
    
    print(f"Carga Trecho: {out_p1.carga_acum_kva}")
    print(f"Temp: {out_p1.cable_temp_celsius}")
    print(f"Status: {out_p1.thermal_status}")
    
    assert out_p1.carga_acum_kva == pytest.approx(99.62, abs=0.01)
    assert out_p1.cable_temp_celsius == pytest.approx(66.5, abs=0.1)
    assert "Ok !" in out_p1.thermal_status

def test_thermal_overload():
    service = LightElectricalService()
    # 240 Cu, I_amp = 430. Sobrecarga > 100%
    # I = 500A. T = 30 + (500/430)*60 = 30 + 69.7 = 99.7C
    # 220V, 3-fases. S = 500 * 0.22 * sqrt(3) = 190.5 kVA
    leitura = 190.5 / 0.375
    
    payload = CqtInputSchema(
        u_nominal=220.0,
        leitura_trafo=leitura,
        trafo_nominal_kva=500,
        lado_1=[
            PosteSchema(id="P1", condutor="240 Cu", comprimento=10, fases=3, ramais=[RamalSchema(tipo="240 Cu", qtd=1)])
        ],
        lado_2=[]
    )
    res = service.calcular_cqt_completo(payload)
    assert res.lado_1[0].cable_temp_celsius > 90
    assert "Reprovado" in res.lado_1[0].thermal_status

def test_thermal_pvc_limit():
    service = LightElectricalService()
    # 53 Al - QX (PVC). Limite 70C.
    # Ampacidade 53 AA é 272.
    # T = 30 + (I/272)*60. Para T > 70 -> (I/272)*60 > 40 -> I/272 > 0.66 -> I > 181A
    # S = 181 * 0.22 * sqrt(3) = 69 kVA.
    leitura = 75 / 0.375 # Carga um pouco maior para garantir Reprovado
    
    payload = CqtInputSchema(
        u_nominal=220.0,
        leitura_trafo=leitura,
        trafo_nominal_kva=500,
        lado_1=[
            PosteSchema(id="P1", condutor="53 Al - QX", comprimento=10, fases=3, ramais=[RamalSchema(tipo="53", qtd=1)])
        ],
        lado_2=[]
    )
    res = service.calcular_cqt_completo(payload)
    res_data = res.lado_1[0]
    # Se Temp > 70.1 deve ser Reprovado
    if res_data.cable_temp_celsius > 70.1:
        assert "Reprovado" in res_data.thermal_status

def test_thermal_single_phase():
    service = LightElectricalService()
    # 1-fase, 127V. 33 AA (205A). 
    # Carga 10 kVA -> I = 10 / 0.127 = 78.74A
    # T = 30 + (78.74/205)*60 = 30 + 23.04 = 53.04C
    payload = CqtInputSchema(
        u_nominal=127.0,
        leitura_trafo=10.0 / 0.375,
        trafo_nominal_kva=112.5,
        lado_1=[
            PosteSchema(id="P1", condutor="33 AA", comprimento=10, fases=1, ramais=[RamalSchema(tipo="33", qtd=1)])
        ],
        lado_2=[]
    )
    res = service.calcular_cqt_completo(payload)
    out = res.lado_1[0]
    assert out.cable_temp_celsius == pytest.approx(53.05, abs=0.1)
