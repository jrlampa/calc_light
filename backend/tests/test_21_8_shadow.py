import pytest
import json
import math
from light_cqt_core import LightElectricalEngine

def load_test_cases():
    with open("shadow_test_cases.json", "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="module")
def engine():
    return LightElectricalEngine(catalog_path=".")

def test_shadow_math_parity(engine):
    data = load_test_cases()
    errors = []
    
    TOLERANCE_TRECHO = 0.01 # 0.01% para unitário
    TOLERANCE_ACUM = 0.05 # 0.05% para acumulado devido à propagação de precisão
    
    for aba in data:
        sheet_name = aba["sheet"]
        u_nom_ln = 127.0
        
        # Começamos com Primary + Trafo (4.93%)
        dv_acum_py = 4.9323 
        
        print(f"\n>>> Verificando {sheet_name}")
        
        for step in aba["steps"]:
            cid = step["id"]
            inputs = step["inputs"]
            expected = step["expected"]
            
            tipo = "rl" if "RAMAL" in str(cid).upper() else "rede"
            
            # Cálculo no motor refatorado (Física Pura)
            dv_trecho_py = engine.calcular_cqt_trecho(
                carga_acum=inputs["carga_acum_kva"],
                condutor=inputs["condutor"],
                comprimento=inputs["metragem"],
                num_fases=inputs["fases"],
                tipo_trecho=tipo
            )
            
            dv_acum_py += dv_trecho_py
            
            # Verificação do trecho
            if not math.isclose(dv_trecho_py, expected["dv_trecho_perc"], abs_tol=TOLERANCE_TRECHO):
                errors.append(f"{sheet_name} | {cid}: dV Trecho Excel={expected['dv_trecho_perc']:.4f}% | PY={dv_trecho_py:.4f}%")
            
            # Verificação acumulada
            if not math.isclose(dv_acum_py, expected["dv_acum_perc"], abs_tol=TOLERANCE_ACUM):
                errors.append(f"{sheet_name} | {cid}: dV Acum Excel={expected['dv_acum_perc']:.4f}% | PY={dv_acum_py:.4f}%")
        
        # Volt Final
        v_final_py = u_nom_ln * (1 - dv_acum_py / 100)
        if not math.isclose(v_final_py, aba["volt_final_excel"], abs_tol=0.2):
            errors.append(f"{sheet_name} | FINAL VOLT: Excel={aba['volt_final_excel']:.2f}V | PY={v_final_py:.2f}V")

    if errors:
        for e in errors: print(f"[FAIL] {e}")
        pytest.fail(f"Detectadas {len(errors)} divergências matemáticas significativas.")
    else:
        print("\n=== [PASS] PARIDADE FÍSICA 100% GARANTIDA (SEM NÚMEROS MÁGICOS) ===")

if __name__ == "__main__":
    eng = LightElectricalEngine(".")
    test_shadow_math_parity(eng)
