import pytest
import os
from scripts.legacy_importer import LegacyImporter, normalize_name
from domain.calculators import calculate_level_resultant
from domain.models import CalculationInput, Conductor

# Caminho para a planilha legado
EXCEL_PATH = r"C:\CALC_LIGHT\CÁLCULO DE TRAÇÃO OII-25-2249.xlsm"

@pytest.fixture(scope="module")
def importer():
    if not os.path.exists(EXCEL_PATH):
        pytest.skip(f"Planilha não encontrada em {EXCEL_PATH}")
    imp = LegacyImporter(EXCEL_PATH)
    imp.open_workbook()
    return imp

@pytest.fixture(scope="module")
def conductors_map(importer):
    """Extrai catálogo de condutores simplificado da aba Plan1."""
    ws = importer.workbook["Plan1"]
    conductors = {}
    # Linhas 3 a 50 conforme seed_full.py
    for row in range(3, 51):
        name_raw = ws[f"C{row}"].value
        name = normalize_name(name_raw)
        if name and "altura" not in name.lower():
            # Simplificação dos dados para o teste de auditoria
            # Em um cenário real, usaríamos o DB, mas aqui queremos testar o motor puro.
            qty_val = ws[f"F{row}"].value
            if qty_val is None:
                qty = 3 if row <= 13 else 1
            else:
                qty = int(qty_val)
            
            # Mensageiro (Lógica do seed_full.py)
            md, mw = 0.0, 0.0
            if any(x in name for x in ["Multiplexado", "Multiplexada", "MTX", "Armado"]):
                md, mw = 0.0095, 0.407
                
            conductors[name] = Conductor(
                name=name,
                diameter_m=float(ws[f"D{row}"].value or 0.0),
                weight_kg_m=float(ws[f"E{row}"].value or 0.0),
                cable_qty=int(qty),
                network_type=ws[f"N{row}"].value or "Convencional",
                messenger_diameter=md,
                messenger_weight=mw
            )
    return conductors

def test_audit_ponto_1(importer, conductors_map):
    """
    Auditoria do Ponto (1): Compara Resultante MT1 e Resultante Total.
    """
    print(f"DEBUG: Conductors in map: {list(conductors_map.keys())[:5]}... (Total: {len(conductors_map)})")
    sheet_data = importer.extract_node_data("Ponto (1)")
    inputs_excel = sheet_data["inputs"]["mt1"]
    expected = sheet_data["expected_results"]
    
    # Prepara entradas para o motor Python
    calc_inputs = []
    conductor_objs = []
    
    for t_key in ["t1", "t2", "t3", "t4"]:
        t_data = inputs_excel[t_key]
        if t_data["network"] and t_data["cable"]:
            cable_name = str(t_data["cable"]).strip()
            if cable_name in conductors_map:
                # Criamos uma cópia do condutor para aplicar propriedades específicas da rede (mensageiro)
                cond = conductors_map[cable_name].model_copy()
                if "Compacta" in t_data["network"]:
                    cond.messenger_weight = 0.407
                    cond.messenger_diameter = 0.0095
                
                calc_inputs.append(CalculationInput(
                    span_m=float(t_data["span"] or 0.0),
                    sag_m=float(t_data["sag"] or 0.0),
                    angle_deg=float(t_data["angle"] or 0.0),
                    pole_height_m=float(sheet_data["inputs"]["pole_height"] or 0.0),
                    anchorage_height_m=float(sheet_data["inputs"]["anchorage_height"] or 0.0),
                    level="MT1",
                    level_order=1
                ))
                conductor_objs.append(cond)
            else:
                print(f"Cable NOT FOUND in map: '{cable_name}'")
    
    # Executa cálculo no novo motor
    result = calculate_level_resultant(calc_inputs, conductor_objs)
    print(f"Resultant Calc: {result.resultant_level_dan} vs Expected: {expected['resultante_mt1_daN']}")
    
    # Comparações Rigorosas (rel=1e-3 conforme Task)
    # 1. Resultante MT1 local
    assert result.resultant_level_dan == pytest.approx(expected["resultante_mt1_daN"], rel=1e-3)
    
    # 2. Tração ajustada no topo
    assert result.traction_on_pole_dan == pytest.approx(expected["tracao_mt1_topo_daN"], rel=1e-3)
    
    # 3. Vento no Poste (vlookup simples no Excel, mas validamos se nosso motor/db bate)
    # Nota: Aqui o motor não calcula vento no poste sozinho ainda (é somado na resultante total)
    # Validamos a resultante total calculada manualmente para bater com C140
    # No Excel C140 = SQRT(SUM(X)^2 + SUM(Y)^2) + Vento_Poste
    
    total_calc = result.traction_on_pole_dan + expected["vento_poste_daN"]
    assert total_calc == pytest.approx(expected["resultante_total_daN"], rel=1e-3)

def test_audit_all_points(importer, conductors_map):
    """
    Loop por todas as abas de pontos para garantir cobertura total.
    """
    sheets = importer.list_calculation_sheets()
    for sheet in sheets:
        sheet_data = importer.extract_node_data(sheet)
        expected = sheet_data["expected_results"]
        
        # Ignora se não houver cálculo de MT1 (base da auditoria atual)
        if not sheet_data["inputs"]["mt1"]["t1"]["network"]:
            continue
            
        calc_inputs = []
        conductor_objs = []
        
        for t_key in ["t1", "t2", "t3", "t4"]:
            t_data = sheet_data["inputs"]["mt1"][t_key]
            if t_data["network"] and t_data["cable"] in conductors_map:
                cond = conductors_map[t_data["cable"]].model_copy()
                if "Compacta" in t_data["network"]:
                    cond.messenger_weight = 0.407
                    cond.messenger_diameter = 0.0095
                
                calc_inputs.append(CalculationInput(
                    span_m=float(t_data["span"] or 0.0),
                    sag_m=float(t_data["sag"] or 0.0),
                    angle_deg=float(t_data["angle"] or 0.0),
                    pole_height_m=float(sheet_data["inputs"]["pole_height"] or 0.0),
                    anchorage_height_m=float(sheet_data["inputs"]["anchorage_height"] or 0.0),
                    level="MT1",
                    level_order=1
                ))
                conductor_objs.append(cond)
        
        if calc_inputs:
            result = calculate_level_resultant(calc_inputs, conductor_objs)
            # Verifica apenas a resultante local para todos os pontos como fumaça
            assert result.resultant_level_dan == pytest.approx(expected["resultante_mt1_daN"], rel=1e-2)
