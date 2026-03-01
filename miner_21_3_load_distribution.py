"""
miner_21_3_load_distribution.py
Fase 21.3b - CACL LIGHT
Rastreamento do Algoritmo de Rateio de Carga (Top-Down + Clandestinos)
Origem: PLANILHA_DESTRAVADA.xlsm (Light / Enel)

Fórmulas extraídas via data_only=False:
─────────────────────────────────────────────────────────────────────────
ETAPA 1 — Peso de cada Poste (Ramais!W_n):
  W_poste = Σ [qtd_ramais[tipo] × Ampacidade[tipo]]
  Tipos: 5,8,13,21,33mm² CC | 13DX,13TX,13QX,21QX,53QX,85QX,107QX | 70,185MMX
  Ampacidades (linha 6): 66,88,116,151,205,272,313,366,418,466,710 A...

ETAPA 2 — Demanda Corrigida (Distrib. Cargas!G9):
  G5  = G3 × 0.375               (G3 = leitura trafo em A ou kVA)
  G9  = G7 × G5 = G7 × G3 × 0.375   (G7 = Fator Temperatura, default 1.0)

ETAPA 3 — Rateio por Poste (Distrib. Cargas!C_n):
  C_poste_n (Lado 1) = G9 × W_L1[n] / (W_Total_L1 + W_Total_L2)
  E_poste_n (Lado 2) = G9 × W_L2[n] / (W_Total_L1 + W_Total_L2)

ETAPA 4 — Carga Acumulada até o Transformador (Distrib. Cargas!D_n):
  D_poste_n = SUM(C_n : C_28)   (soma do poste n até o último = carga no início do trecho)

CLASSES (Ramais linhas 13-15):
  Coef_QDT = R × FP_cos + X × FP_sin
  Comercial:   FP_cos=0.85, FP_sin=0.5268
  Residencial: FP_cos=0.95, FP_sin=0.3122
  Misto:       FP_cos=0.90, FP_sin=0.4359
─────────────────────────────────────────────────────────────────────────
"""

import json
import re
import warnings
import openpyxl

warnings.filterwarnings("ignore")

XLSM_PATH = "PLANILHA_DESTRAVADA.xlsm"
OUT_LOAD = "load_distribution_logic.json"

# Colunas de condutores na aba Ramais (índice base 1)
# B=2(label) | C=3..V=22 (condutores) | W=23 (peso total)
COL_LABEL       = 2   # B = nome do poste
COL_COND_START  = 3   # C
COL_COND_END    = 22  # V
COL_PESO        = 23  # W
ROW_CONDUTOR    = 4   # linha 4 = bitola (5, 8, 13, ...)
ROW_MATERIAL    = 5   # linha 5 = material (CC, AWG, MMX...)
ROW_AMPACIDADE  = 6   # linha 6 = Ampacidade (A)
ROW_LADO1_START = 25  # Poste 1 Lado 1
ROW_LADO1_END   = 49  # Poste 25 Lado 1
ROW_LADO1_TOTAL = 50  # W50 = SUM(W25:W49)
ROW_LADO2_START = 56  # Poste 1 Lado 2
ROW_LADO2_END   = 80  # Poste 25 Lado 2
ROW_LADO2_TOTAL = 81  # W81 = SUM(W56:W80)

# Linhas dos fatores de classe
ROW_COMERCIAL   = 13
ROW_RESIDENCIAL = 14
ROW_MISTO       = 15

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def sanitize_str(value) -> str:
    if value is None:
        return ""
    return re.sub(r" {2,}", " ", re.sub(r"[\r\n\t]+", " ", str(value))).strip()

def to_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    # Remove fórmula caso data_only=False retorne strings com '='
    if text.startswith("="):
        return None
    try:
        return float(text)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# EXTRAÇÃO 1 — CATÁLOGO DE CONDUTORES COM AMPACIDADE
# ---------------------------------------------------------------------------
def extract_conductor_ampacity(ws_ramais) -> list[dict]:
    """
    Aba Ramais, linha 4 (bitola) + linha 5 (material) + linha 6 (ampacidade).
    Retorna lista de condutores com seus Índices de Ampacidade.
    """
    conductors = []
    for col in range(COL_COND_START, COL_COND_END + 1):
        bitola   = sanitize_str(ws_ramais.cell(row=ROW_CONDUTOR, column=col).value)
        material = sanitize_str(ws_ramais.cell(row=ROW_MATERIAL, column=col).value)
        amp      = to_float(ws_ramais.cell(row=ROW_AMPACIDADE, column=col).value)
        if not bitola and not material:
            continue
        # Nome amigável: preferência para material se diferente de bitola
        name = material if (material and material not in ("CC",)) else bitola
        conductors.append({
            "col_index": col,
            "conductor_name": name or bitola,
            "bitola": bitola,
            "material": material,
            "ampacity_a": amp,
        })
    return conductors


# ---------------------------------------------------------------------------
# EXTRAÇÃO 2 — PESOS DOS POSTES POR LADO (W_n = soma ponderada de ramais)
# ---------------------------------------------------------------------------
def extract_pole_weights(ws_ramais, conductors: list[dict], row_start: int, row_end: int, row_total: int) -> dict:
    """
    Extrai os pesos W_n de cada poste (produto de ramais × ampacidade).
    A fórmula real é: W_n = Σ [qtd_ramal[tipo] × Ampacidade[tipo]]
    Retorna: lista de postes com peso individual, e total Σ W.
    """
    poles = []
    for row in range(row_start, row_end + 1):
        label_raw = ws_ramais.cell(row=row, column=COL_LABEL).value
        label = sanitize_str(label_raw) if label_raw else f"Linha {row}"

        # Quantidade de ramais por tipo de condutor
        ramais_by_conductor = {}
        peso_calculado = 0.0

        for cond in conductors:
            qtd_raw = ws_ramais.cell(row=row, column=cond["col_index"]).value
            qtd = to_float(qtd_raw)
            if qtd and qtd > 0 and cond["ampacity_a"]:
                ramais_by_conductor[cond["conductor_name"]] = qtd
                peso_calculado += qtd * cond["ampacity_a"]

        # Tenta também ler o W calculado pela planilha (data_only pode retornar NULL)
        w_celula = to_float(ws_ramais.cell(row=row, column=COL_PESO).value)

        poles.append({
            "poste_label": label,
            "row": row,
            "ramais_por_condutor": ramais_by_conductor,
            "peso_w_calculado": round(peso_calculado, 2),
            "peso_w_planilha": w_celula,
        })

    # Peso total
    w_total_planilha = to_float(ws_ramais.cell(row=row_total, column=COL_PESO).value)
    w_total_calculado = sum(p["peso_w_calculado"] for p in poles)

    return {
        "postes": poles,
        "w_total_planilha": w_total_planilha,
        "w_total_calculado": round(w_total_calculado, 2),
    }


# ---------------------------------------------------------------------------
# EXTRAÇÃO 3 — ALGORITMO TOP-DOWN: Árvore de Fórmulas (Distrib. Cargas)
# ---------------------------------------------------------------------------
def extract_top_down_formulas(ws_distrib) -> dict:
    """
    Mapeia a árvore de fórmulas de Distrib. Cargas com data_only=False.
    Células-chave: G3(input), G5(dem_max), G7(fator_temp), G9(dem_corrigida)
    Padrão de cada poste: C_n = G9 × (W_L1[n] / (W_Total_L1 + W_Total_L2))
    """
    # Lê fórmulas-chave
    def formula(row, col):
        val = ws_distrib.cell(row=row, column=col).value
        return sanitize_str(val) if val else None

    return {
        "entrada": {
            "G3": {"descricao": "Leitura do Transformador (input manual do usuário)", "formula": "INPUT"},
            "G5": {"descricao": "Demanda Máxima = G3 × 0.375", "formula": formula(5, 7)},
            "G6": {"descricao": "Fator de Temperatura (label)", "formula": "LABEL"},
            "G7": {"descricao": "Fator de Temperatura (valor)", "formula": formula(7, 7)},
            "G8": {"descricao": "Demanda Corrigida (label)", "formula": "LABEL"},
            "G9": {"descricao": "Demanda Corrigida = G7 × G5", "formula": formula(9, 7)},
        },
        "rateio_por_poste": {
            "descricao": "Para cada poste n (linha 5..28 = Postes 1..25):",
            "formula_carga_lado1": "C_n = IF(G9='','', G9 × (Ramais!W[n_L1] / (Ramais!W50 + Ramais!W81)))",
            "formula_carga_lado2": "E_n = IF(G9='','', G9 × (Ramais!W[n_L2] / (Ramais!W50 + Ramais!W81)))",
            "formula_carga_acum_lado1": "D_n = SUM(C_n : C_28)  ← carga total até o trafo a partir do poste n",
            "formula_carga_acum_lado2": "F_n = SUM(E_n : E_28)",
        },
        "fórmula_C5_exemplo": formula(5, 3),   # C5
        "fórmula_C9_exemplo": formula(9, 3),   # C9 (poste 5)
    }


# ---------------------------------------------------------------------------
# EXTRAÇÃO 4 — FATORES DE CLASSE (Coeficientes QDT por perfil de carga)
# ---------------------------------------------------------------------------
def extract_class_qdt_coefficients(ws_ramais) -> dict:
    """
    Linha 13 = Comercial:   K = R × 0.85 + X × 0.5268
    Linha 14 = Residencial: K = R × 0.95 + X × 0.3122
    Linha 15 = Misto:       K = R × 0.90 + X × 0.4359
    FP (Fator de Potência) implícito em cada par (cos, sin).
    """
    CLASSES = {
        ROW_COMERCIAL:   {"nome": "Comercial",   "fp_cos": 0.85, "fp_sin": 0.5268},
        ROW_RESIDENCIAL: {"nome": "Residencial", "fp_cos": 0.95, "fp_sin": 0.3122},
        ROW_MISTO:       {"nome": "Misto",       "fp_cos": 0.90, "fp_sin": 0.4359},
    }

    result = {}
    for row, meta in CLASSES.items():
        formula_celula = sanitize_str(ws_ramais.cell(row=row, column=COL_COND_START).value)
        result[meta["nome"]] = {
            "fp_cos": meta["fp_cos"],
            "fp_sin": meta["fp_sin"],
            "formula_K_por_condutor":
                f"K = R × {meta['fp_cos']} + X × {meta['fp_sin']}",
            "formula_celula_exemplo_C{row}": formula_celula,
            "descricao": (
                f"Coeficiente QDT efetivo considerando FP={meta['fp_cos']} "
                f"→ sin(φ)={meta['fp_sin']}. "
                f"ΔV% = K × I_A × L_km"
            ),
        }

    return result


# ---------------------------------------------------------------------------
# EXTRAÇÃO 5 — ALGORITMO BOTTOM-UP (Clandestinos)
# Dados da aba ANÁLISE PONTO A PONTO: kVA/cliente = 2.22 (constante da Light)
# O usuário revelou que 2.22 kVA corresponde ao perfil de 60m² de área.
# ---------------------------------------------------------------------------
def extract_clandestino_profiles() -> dict:
    """
    Perfil de área × demanda para clientes clandestinos (dado revelado pelo usuário).
    A constante 2.22 kVA verificada na Fase 21.3 é o padrão da Light para 60m².
    """
    return {
        "fonte": "ANÁLISE PONTO A PONTO + regra de negócio revelada pelo usuário",
        "kva_por_cliente_base": 2.22,
        "perfil_area_60m2_kva": 2.22,
        "nota": (
            "Para áreas clandestinas, a Light estimativa 2.22 kVA por unidade. "
            "Este valor corresponde ao porte de uma UC residencial de ~60m². "
            "A demanda agregada aplica o Fator de Diversificação da curva "
            "'ANÁLISE PONTO A PONTO': ΔV% = K × Demanda(N) × L_km "
            "onde Demanda(N) = 2.22 × FatorDiv(N)."
        ),
        "formula_fator_diversificacao": {
            "plateau_inferior": {"condicao": "N ≤ 4", "fator": 3.88},
            "zona_linear": {
                "condicao": "5 ≤ N ≤ 295",
                "formula": "FatorDiv(N) = 3.88 + (N - 4) × 0.56",
            },
            "plateau_superior": {"condicao": "N ≥ 296", "fator": 83.00},
        },
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    print(f"[ETL] Carregando {XLSM_PATH} (data_only=False — lendo fórmulas)...")
    wb = openpyxl.load_workbook(XLSM_PATH, keep_vba=True, data_only=False)

    ws_ramais  = wb["Ramais"]
    ws_distrib = wb["Distrib. Cargas"]

    # 1 — Condutores + Ampacidade
    conductors = extract_conductor_ampacity(ws_ramais)
    print(f"[ETL] Condutores mapeados: {len(conductors)}")

    # 2 — Pesos por Poste
    lado1 = extract_pole_weights(ws_ramais, conductors, ROW_LADO1_START, ROW_LADO1_END, ROW_LADO1_TOTAL)
    lado2 = extract_pole_weights(ws_ramais, conductors, ROW_LADO2_START, ROW_LADO2_END, ROW_LADO2_TOTAL)
    print(f"[ETL] Postes Lado 1: {len(lado1['postes'])} | W_total={lado1['w_total_planilha']}")
    print(f"[ETL] Postes Lado 2: {len(lado2['postes'])} | W_total={lado2['w_total_planilha']}")

    # 3 — Árvore de fórmulas top-down
    top_down = extract_top_down_formulas(ws_distrib)
    print("[ETL] Fórmulas Distrib. Cargas extraídas.")

    # 4 — Coeficientes de classe QDT
    class_coefs = extract_class_qdt_coefficients(ws_ramais)
    print(f"[ETL] Classes QDT: {list(class_coefs.keys())}")

    # 5 — Perfil clandestinos
    clandestinos = extract_clandestino_profiles()

    # ---- OUTPUT ----
    output = {
        "_metadata": {
            "fase": "21.3b",
            "projeto": "CACL LIGHT",
            "fonte": XLSM_PATH,
            "descricao": "Algoritmo de Rateio de Carga: Top-Down (Rede Normal) e Bottom-Up (Clandestinos)",
        },
        "catalogo_condutores_ampacidade": conductors,
        "pesos_postes": {
            "lado_1_Trafo": lado1,
            "lado_2_Trafo": lado2,
        },
        "algoritmo_top_down_formulas": top_down,
        "coeficientes_qdt_por_classe": class_coefs,
        "algoritmo_bottom_up_clandestinos": clandestinos,
    }

    with open(OUT_LOAD, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[ETL] ✔ Gerado: {OUT_LOAD}")

    # ---- RESUMO ----
    print("\n[RESUMO DA ÁRVORE TOP-DOWN]")
    td = top_down["entrada"]
    print(f"  G3 (input trafo): {td['G3']['descricao']}")
    print(f"  G5 = {td['G5']['formula']}")
    print(f"  G7 = {td['G7']['formula']}")
    print(f"  G9 = {td['G9']['formula']}")
    print(f"\n  Rateio Poste_n (Lado 1):")
    print(f"    {top_down['rateio_por_poste']['formula_carga_lado1']}")
    print(f"\n  Onde W_Poste_n:")
    print(f"    W_n = Σ [qtd_ramais[tipo] × Ampacidade[tipo]]")
    print(f"    W_n_exemplo (fórmula planilha): {top_down['fórmula_C5_exemplo']}")

    print(f"\n[RESUMO BOTTOM-UP CLANDESTINOS]")
    print(f"  {clandestinos['nota']}")


if __name__ == "__main__":
    main()
