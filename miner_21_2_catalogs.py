"""
miner_21_2_catalogs.py
Fase 21.2 - CACL LIGHT
ETL: Extração, Sanitização e Exportação de Catálogos Elétricos
Origem: PLANILHA_DESTRAVADA.xlsm (Light / Enel)
Saída: cables_catalog_light.json | transformers_catalog_light.json

Coordenadas confirmadas via miner_21_1_topology.py (Fase 21.1):
  Ramais!B4:T6   → Cabeçalhos BT (condutores, material)
  Ramais!B11:T11 → Resistência R (Ohms)
  Ramais!B12:T12 → Reatância X (Ohms)
  Ramais!B6:T6   → Ampacidade (A)
  Tabela!B7:F27  → Cabos BT Rede/Concêntrico (Seção, Rca, jXL)
  Tabela!C32:G35 → Cabos MT Subterrâneos (R, jX)
  Tabela!C37:I40 → Cabos MT Aéreos (R, jX)
  Coeficiente Unitário!B5:E18 → K coef. de QDT por cabo (CRÍTICO para CQT)
  Alocação % de tensão!B48:I56  → Trafo Tab_B (Aéreo-Aéreo)
  Alocação % de tensão!B64:I72  → Trafo Tab_C (Aéreo-Subterrâneo)
  Alocação % de tensão!B79:I80  → Trafo Tab_D (Reticulado)
"""

import json
import re
import warnings
import openpyxl

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# CONSTANTES DE CONFIGURAÇÃO
# ---------------------------------------------------------------------------
XLSM_PATH = "PLANILHA_DESTRAVADA.xlsm"
OUT_CABLES = "cables_catalog_light.json"
OUT_TRANSFORMERS = "transformers_catalog_light.json"
OUT_COEF = "voltage_drop_coef_light.json"


# ---------------------------------------------------------------------------
# HELPERS DE SANITIZAÇÃO
# ---------------------------------------------------------------------------
def sanitize_str(value) -> str:
    """Remove espaços extras, quebras de linha e retorna string limpa."""
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"[\r\n\t]+", " ", text)   # quebras → espaço
    text = re.sub(r" {2,}", " ", text)         # espaços duplos
    return text.strip()


def to_float(value) -> float | None:
    """Converte valor para float tratando padrão PT-BR (vírgula decimal)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", ".")  # PT-BR → EN
    try:
        return float(text)
    except ValueError:
        return None


def cell_val(ws, row: int, col: int):
    """Lê e retorna o valor bruto de uma célula."""
    return ws.cell(row=row, column=col).value


# ---------------------------------------------------------------------------
# EXTRAÇÃO 1 — CATÁLOGO BT (Aba: Ramais)
# Estrutura: cabeçalho transposto (condutor na col, propriedade na linha)
# ---------------------------------------------------------------------------
def extract_bt_ramal_catalog(ws) -> list[dict]:
    """
    Aba Ramais: extrai condutores BT.
    Linha 4  → Seção/Nome do condutor  (B4..T4 + B5..T5, junção)
    Linha 5  → Material (CC = Cobre Compacto, AWG, etc.)
    Linha 6  → Ampacidade [A]
    Linha 11 → R (Ohms/km)
    Linha 12 → X (Ohms/km)
    Condutores nas colunas C..T (col 3..20); col B são labels.
    """
    catalogs = []

    # Nome do condutor: linha 4 (bitola numérica) + linha 5 (código/AWG)
    header_row_4 = [cell_val(ws, 4, c) for c in range(3, 21)]  # C4..T4
    header_row_5 = [cell_val(ws, 5, c) for c in range(3, 21)]  # C5..T5
    ampacity_row = [cell_val(ws, 6, c) for c in range(3, 21)]
    r_row = [cell_val(ws, 11, c) for c in range(3, 21)]
    x_row = [cell_val(ws, 12, c) for c in range(3, 21)]

    for i in range(len(header_row_4)):
        # Monta o nome: prioriza linha 5 (mais específico), complementa com linha 4
        name_4 = sanitize_str(header_row_4[i]) if header_row_4[i] else ""
        name_5 = sanitize_str(header_row_5[i]) if header_row_5[i] else ""

        if name_5 and name_5 not in ("CC",):   # CC = só material, não nome
            conductor_name = name_5
        elif name_4:
            conductor_name = name_4
        else:
            continue  # coluna vazia ou apenas material

        material = "CC" if name_5 == "CC" else name_5  # AWG / CCM / etc.

        r_val = to_float(r_row[i])
        x_val = to_float(x_row[i])
        amp_val = to_float(ampacity_row[i])

        if r_val is None and x_val is None:
            continue  # linha sem dados elétricos

        catalogs.append({
            "source": "Ramais",
            "voltage_level": "BT",
            "conductor_name": conductor_name,
            "section_mm2": None,       # AWG/MCM — não temos mm² direto aqui
            "material": material,
            "r_ohm_per_km": r_val,
            "x_ohm_per_km": x_val,
            "ampacity_a": amp_val,
            "conductor_type": "multiplex_aerial",
        })

    return catalogs


# ---------------------------------------------------------------------------
# EXTRAÇÃO 2 — CATÁLOGO BT/MT Rede (Aba: Tabela, linhas 7–27)
# Estrutura: coluna B = seção/nome, C = Rca (Z1Z2), D = jXL, E = Rca(Z0), F = jXL(Z0)
# ---------------------------------------------------------------------------
def extract_tabela_bt_catalog(ws) -> list[dict]:
    """
    Aba Tabela, B7:F27 → cabos BT de rede (subterrâneos e multiplex).
    B = Nome (seção + material + tipo)
    C = Rca Z1Z2 (Ω/km)  D = jXL Z1Z2 (Ω/km)
    E = Rca Z0   (Ω/km)  F = jXL Z0  (Ω/km)
    """
    catalogs = []
    for row in range(7, 28):  # linhas 7..27
        name_raw = cell_val(ws, row, 2)  # col B
        if name_raw is None:
            continue
        name = sanitize_str(name_raw)
        if not name or "REF" in name:
            continue

        rca_z1 = to_float(cell_val(ws, row, 3))   # C
        jxl_z1 = to_float(cell_val(ws, row, 4))   # D
        rca_z0 = to_float(cell_val(ws, row, 5))   # E
        jxl_z0 = to_float(cell_val(ws, row, 6))   # F

        if rca_z1 is None:
            continue

        # Inferir material a partir do nome
        material = "Al" if " Al" in name or "Al -" in name else \
                   "Cu" if " Cu" in name or "CONC" in name else "N/A"
        vl = "BT" if any(k in name for k in ["CONC", "DX", "TX", "QX", "MX", "AWG"]) else "BT/MT"

        catalogs.append({
            "source": "Tabela",
            "voltage_level": vl,
            "conductor_name": name,
            "section_mm2": None,
            "material": material,
            "r_ohm_per_km": rca_z1,
            "x_ohm_per_km": jxl_z1,
            "r_z0_ohm_per_km": rca_z0,
            "x_z0_ohm_per_km": jxl_z0,
            "ampacity_a": None,
            "conductor_type": "network",
        })

    return catalogs


# ---------------------------------------------------------------------------
# EXTRAÇÃO 3 — CATÁLOGO MT Subterrâneo (Aba: Tabela, linhas 32–35)
# Estrutura: cabeçalho na linha 33 (C..G), dados nas linhas 34–35
# ---------------------------------------------------------------------------
def extract_mt_subterraneo(ws) -> list[dict]:
    """
    Aba Tabela, C32:G35 → cabos MT Subterrâneos.
    Linha 33 → nomes dos cabos (C..G)
    Linha 34 → R (Ω/km)
    Linha 35 → jX (Ω/km)
    """
    catalogs = []
    header_cols = range(3, 8)  # C=3..G=7

    names = [sanitize_str(cell_val(ws, 33, c)) for c in header_cols]
    r_vals = [to_float(cell_val(ws, 34, c)) for c in header_cols]
    x_vals = [to_float(cell_val(ws, 35, c)) for c in header_cols]

    for i, name in enumerate(names):
        if not name or r_vals[i] is None:
            continue
        section = _parse_section(name)
        material = "Cu" if "Cu" in name else "Al"
        catalogs.append({
            "source": "Tabela",
            "voltage_level": "MT",
            "conductor_name": name,
            "section_mm2": section,
            "material": material,
            "r_ohm_per_km": r_vals[i],
            "x_ohm_per_km": x_vals[i],
            "ampacity_a": None,
            "conductor_type": "underground",
        })

    return catalogs


# ---------------------------------------------------------------------------
# EXTRAÇÃO 4 — CATÁLOGO MT Aéreo (Aba: Tabela, linhas 37–40)
# Estrutura: cabeçalho na linha 38 (C..I), dados nas linhas 39–40
# ---------------------------------------------------------------------------
def extract_mt_aereo(ws) -> list[dict]:
    """
    Aba Tabela, C37:I40 → cabos MT Aéreos.
    Linha 38 → nomes dos cabos (C..I)
    Linha 39 → R (Ω/km)
    Linha 40 → jX (Ω/km)
    """
    catalogs = []
    header_cols = range(3, 10)  # C=3..I=9

    names = [sanitize_str(cell_val(ws, 38, c)) for c in header_cols]
    r_vals = [to_float(cell_val(ws, 39, c)) for c in header_cols]
    x_vals = [to_float(cell_val(ws, 40, c)) for c in header_cols]

    for i, name in enumerate(names):
        if not name or r_vals[i] is None:
            continue
        section = _parse_section(name)
        material = "Cu" if "Cu" in name or "PR" in name else "Al"
        catalogs.append({
            "source": "Tabela",
            "voltage_level": "MT",
            "conductor_name": name,
            "section_mm2": section,
            "material": material,
            "r_ohm_per_km": r_vals[i],
            "x_ohm_per_km": x_vals[i],
            "ampacity_a": None,
            "conductor_type": "aerial",
        })

    return catalogs


# ---------------------------------------------------------------------------
# EXTRAÇÃO 5 — CATÁLOGO DE TRANSFORMADORES (Aba: Alocação % de tensão)
# Estrutura: múltiplos blocos com Potência(kVA) + Queda no Trafo
# ---------------------------------------------------------------------------
def extract_transformers(ws) -> list[dict]:
    """
    Aba 'Alocação % de tensão'.
    Estrutura real: tabelas com múltiplas linhas de dados de potência.
    Colunas: B=kVA, C=FatorCoinc%, D=V_prim, E=V_sec,
             F=dV_rede_prim%, G=dV_trafo%, H=dV_rede_sec%, I=dV_ramal%

    Blocos (linha de dados reais):
    Tab B (Aéreo-Aéreo): linhas 48,50,52,54,56
    Tab C (Aéreo-Subterrâneo): linhas 64,66,68,70,72
    Tab D (Reticulado): linha 79
    """
    data_rows = [
        *[(r, "Tab_B_Aereo-Aereo") for r in range(48, 58, 2)],
        *[(r, "Tab_C_Aereo-Subterraneo") for r in range(64, 74, 2)],
        (79, "Tab_D_Reticulado"),
    ]

    transformers = []
    seen = set()

    for row, tab_label in data_rows:
        kva_raw = cell_val(ws, row, 2)  # col B
        if kva_raw is None:
            continue
        kva_str = sanitize_str(str(kva_raw))
        if not kva_str or any(x in kva_str for x in ["kVA", "Potência", "RETICULADO", "Até"]):
            continue

        kva_val = to_float(re.sub(r"[^0-9\.]", "", kva_str))
        if kva_val is None:
            continue

        key = f"{kva_val}_{tab_label}"
        if key in seen:
            continue
        seen.add(key)

        transformers.append({
            "source": "Alocação % de tensão",
            "tabela": tab_label,
            "power_kva": kva_val,
            "coincidence_factor_pct": to_float(cell_val(ws, row, 3)),
            "primary_voltage_v": to_float(cell_val(ws, row, 4)),
            "secondary_voltage_v": to_float(cell_val(ws, row, 5)),
            "dv_primary_pct": to_float(cell_val(ws, row, 6)),
            "dv_transformer_pct": to_float(cell_val(ws, row, 7)),
            "dv_secondary_pct": to_float(cell_val(ws, row, 8)),
            "dv_branch_pct": to_float(cell_val(ws, row, 9)),
        })

    return transformers


# ---------------------------------------------------------------------------
# EXTRAÇÃO 6 — COEFICIENTE UNITÁRIO (Aba: Coeficiente Unitário)
# DADO CRÍTICO: K = coeficiente de queda de tensão por cabo para CQT
# ---------------------------------------------------------------------------
def extract_coef_unitario(ws) -> list[dict]:
    """
    Aba 'Coeficiente Unitário' (oculta) — DADO CRÍTICO PARA CQT.
    Contém o coeficiente K de queda de tensão por condutor.
    Fórmula implícita: dV% = K * kVA * L(km)
    B3:E18 → B=Nome Cabo, C=R(Ω/km), D=X(Ω/km), E=Coef. Queda K
    Dados nas linhas 5..18.
    """
    coefs = []
    for row in range(5, 19):
        name_raw = cell_val(ws, row, 2)  # col B
        if name_raw is None:
            continue
        name = sanitize_str(name_raw)
        if not name:
            continue

        coefs.append({
            "source": "Coeficiente Unitário",
            "conductor_name": name,
            "r_ohm_per_km": to_float(cell_val(ws, row, 3)),
            "x_ohm_per_km": to_float(cell_val(ws, row, 4)),
            "voltage_drop_coef_k": to_float(cell_val(ws, row, 5)),   # K: dV% = K * kVA * L
        })

    return coefs


# ---------------------------------------------------------------------------
# HELPER: parse seção mm² do nome do cabo
# ---------------------------------------------------------------------------
def _parse_section(name: str) -> float | None:
    """Tenta extrair seção em mm² do primeiro número no nome do condutor."""
    match = re.match(r"(\d+(?:[,\.]\d+)?)", name)
    if match:
        return to_float(match.group(1))
    return None


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    print(f"[ETL] Carregando {XLSM_PATH}...")
    wb = openpyxl.load_workbook(XLSM_PATH, keep_vba=True, data_only=True)

    # ---- CABOS ----
    ws_ramais = wb["Ramais"]
    ws_tabela = wb["Tabela"]

    cables = []
    cables.extend(extract_bt_ramal_catalog(ws_ramais))
    cables.extend(extract_tabela_bt_catalog(ws_tabela))
    cables.extend(extract_mt_subterraneo(ws_tabela))
    cables.extend(extract_mt_aereo(ws_tabela))

    print(f"[ETL] Cabos extraídos: {len(cables)}")
    with open(OUT_CABLES, "w", encoding="utf-8") as f:
        json.dump(cables, f, ensure_ascii=False, indent=2)
    print(f"[ETL] ✔ Gerado: {OUT_CABLES}")

    # ---- COEFICIENTE UNITÁRIO (K de QDT) ----
    ws_coef = wb["Coeficiente Unitário"]
    coefs = extract_coef_unitario(ws_coef)

    print(f"[ETL] Coeficientes de QDT extraídos: {len(coefs)}")
    with open(OUT_COEF, "w", encoding="utf-8") as f:
        json.dump(coefs, f, ensure_ascii=False, indent=2)
    print(f"[ETL] ✔ Gerado: {OUT_COEF}")

    # ---- TRANSFORMADORES ----
    ws_aloc = wb["Alocação % de tensão"]
    transformers = extract_transformers(ws_aloc)

    print(f"[ETL] Transformadores extraídos: {len(transformers)}")
    with open(OUT_TRANSFORMERS, "w", encoding="utf-8") as f:
        json.dump(transformers, f, ensure_ascii=False, indent=2)
    print(f"[ETL] ✔ Gerado: {OUT_TRANSFORMERS}")

    print("\n[ETL] Fase 21.2 concluída com sucesso!")
    print(f"  → {OUT_CABLES}          ({len(cables)} condutores)")
    print(f"  → {OUT_COEF}  ({len(coefs)} coeficientes K)")
    print(f"  → {OUT_TRANSFORMERS}  ({len(transformers)} cenários)")


if __name__ == "__main__":
    main()
