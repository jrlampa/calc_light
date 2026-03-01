"""
miner_21_3_demand.py
Fase 21.3 - CACL LIGHT
Mineração do Fator de Demanda / Simultaneidade (Diversificação)
Origem: PLANILHA_DESTRAVADA.xlsm (Light / Enel)
Saída: demand_curve_light.json

Coordenadas confirmadas via dump_demand_sheets.py (Fase 21.3):
  ANÁLISE PONTO A PONTO!P4:S304 → Tabela principal de demanda
    P = QTD Clientes (1..N)
    Q = Fator por Área [kVA/cliente] (base = 2.22, constante)
    R = Fator de Diversificação (cresce com o número de clientes)
    S = Demanda Agregada [kVA] = Q * R

  Ramais!B13:O15 → Fatores de demanda por classe (Comercial/Residencial/Misto)
    Linha 13 = Comercial    → coeficiente de QDT por número de ramais
    Linha 14 = Residencial  → coeficiente de QDT por número de ramais
    Linha 15 = Misto        → coeficiente de QDT por número de ramais
"""

import json
import re
import warnings
import openpyxl

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# CONSTANTES
# ---------------------------------------------------------------------------
XLSM_PATH = "PLANILHA_DESTRAVADA.xlsm"
OUT_DEMAND = "demand_curve_light.json"

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def sanitize_str(value) -> str:
    if value is None:
        return ""
    text = re.sub(r"[\r\n\t]+", " ", str(value))
    return re.sub(r" {2,}", " ", text).strip()

def to_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# EXTRAÇÃO 1 — TABELA PRINCIPAL DE DEMANDA
# Aba: ANÁLISE PONTO A PONTO  |  Colunas P(16), Q(17), R(18), S(19)
# Linhas 4..304 (tabela pode continuar além disso)
# ---------------------------------------------------------------------------
def extract_demand_table(ws) -> dict:
    """
    Extrai a tabela P(QTD_clientes), Q(kVA/cliente), R(FatorDiv), S(Demanda_kVA).
    Retorna estrutura aninhada com:
      - tabela_completa: lista de dicionários por número de clientes
      - kva_por_cliente_base: o valor unitário de kVA (Q, constante)
      - regra_limite: comportamento para N além da tabela
      - step_fator_diversificacao: incremento linear observado
    """
    COL_CLIENTES = 16   # P
    COL_KVA_UNIT = 17  # Q
    COL_FATOR    = 18  # R
    COL_DEMANDA  = 19  # S

    rows_data = []
    max_r = min(ws.max_row, 305)

    for row in range(4, max_r + 1):
        n_cli   = to_float(ws.cell(row=row, column=COL_CLIENTES).value)
        kva_u   = to_float(ws.cell(row=row, column=COL_KVA_UNIT).value)
        f_div   = to_float(ws.cell(row=row, column=COL_FATOR).value)
        dem_kva = to_float(ws.cell(row=row, column=COL_DEMANDA).value)

        if n_cli is None or f_div is None:
            continue

        rows_data.append({
            "n_clientes": int(n_cli),
            "kva_por_cliente": round(kva_u, 4) if kva_u else None,
            "fator_diversificacao": round(f_div, 4),
            "demanda_kva": round(dem_kva, 4) if dem_kva else None,
        })

    if not rows_data:
        return {}

    # Detectar comportamento linear  (análise de incremento de Fator)
    increments = []
    for i in range(1, len(rows_data)):
        delta = rows_data[i]["fator_diversificacao"] - rows_data[i-1]["fator_diversificacao"]
        increments.append(round(delta, 4))

    # Calcular step modal (mais frequente)
    if increments:
        from collections import Counter
        step_modal = Counter(increments).most_common(1)[0][0]
    else:
        step_modal = None

    # kVA unitário base (deve ser constante = Q)
    kva_units = set(r["kva_por_cliente"] for r in rows_data if r["kva_por_cliente"])
    kva_base = round(float(list(kva_units)[0]), 4) if len(kva_units) == 1 else None
    kva_note = "CONSTANTE" if len(kva_units) == 1 else f"VARIÁVEL: {sorted(kva_units)}"

    # Regra do limite (N além da tabela)
    ultimo = rows_data[-1]
    regra_limite = (
        f"Para N > {ultimo['n_clientes']}: extrapolar linearmente com "
        f"step de fator_diversificacao = {step_modal} por cliente adicional. "
        f"Demanda = {kva_base} * (fator_diversificacao)"
    )

    # Análise de plateau inicial (primeiros clientes têm fator fixo?)
    plateau_rows = [r for r in rows_data if r["fator_diversificacao"] == rows_data[0]["fator_diversificacao"]]
    plateau_ate = plateau_rows[-1]["n_clientes"] if len(plateau_rows) > 1 else 1

    return {
        "fonte": "ANÁLISE PONTO A PONTO (visible)",
        "colunas": {"P": "QTD_Clientes", "Q": "kVA/cliente", "R": "Fator_Diversificacao", "S": "Demanda_kVA"},
        "kva_por_cliente_base": kva_base,
        "kva_por_cliente_nota": kva_note,
        "plateau_inicial_ate_n_clientes": plateau_ate,
        "plateau_fator": rows_data[0]["fator_diversificacao"],
        "step_fator_diversificacao_por_cliente": step_modal,
        "n_max_tabelado": ultimo["n_clientes"],
        "regra_limite_excedente": regra_limite,
        "tabela": rows_data,
    }


# ---------------------------------------------------------------------------
# EXTRAÇÃO 2 — FATORES POR CLASSE (Residencial / Comercial / Misto)
# Aba: Ramais  |  Linhas 13-15, Colunas C..O (3..15)
# Estrutura: cabeçalhos dos condutores na linha 4 e linha 5
# Linha 13 = Comercial, Linha 14 = Residencial, Linha 15 = Misto
# Esses são coeficientes de QDT por condutor para cada perfil de carga
# ---------------------------------------------------------------------------
def extract_class_factors(ws) -> dict:
    """
    Aba Ramais: extrai fatores de QDT por classe de consumidor.
    Linhas 13-15 (Comercial, Residencial, Misto).
    Cabeçalhos dos condutores: linha 4 (número) + linha 5 (código).
    """
    CLASS_MAP = {13: "Comercial", 14: "Residencial", 15: "Misto"}
    COL_RANGE = range(3, 16)  # C..O

    # Coletar cabeçalhos
    headers = []
    for col in COL_RANGE:
        name_4 = sanitize_str(ws.cell(row=4, column=col).value)
        name_5 = sanitize_str(ws.cell(row=5, column=col).value)
        label = name_5 if name_5 and name_5 not in ("CC",) else name_4
        headers.append(label)

    result = {}
    for row, class_name in CLASS_MAP.items():
        row_label = sanitize_str(ws.cell(row=row, column=2).value)  # col B
        factors = {}
        for i, col in enumerate(COL_RANGE):
            val = to_float(ws.cell(row=row, column=col).value)
            if val is not None and headers[i]:
                factors[headers[i]] = val
        result[class_name] = {
            "label_planilha": row_label,
            "coeficientes_qdt_por_condutor": factors,
            "nota": "Coeficiente acumulado: QDT_total% = Coef × I × (L/1000) para cada condutor",
        }

    return result


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    print(f"[ETL] Carregando {XLSM_PATH}...")
    wb = openpyxl.load_workbook(XLSM_PATH, keep_vba=True, data_only=True)

    # ---- TABELA PRINCIPAL DE DEMANDA ----
    # Encontra aba pelo nome (pode ter encoding diferente)
    ws_demand = None
    for name in wb.sheetnames:
        if "PONTO" in name.upper():
            ws_demand = wb[name]
            break
    if ws_demand is None:
        print("[ERRO] Aba 'ANÁLISE PONTO A PONTO' não encontrada.")
        return

    demand_data = extract_demand_table(ws_demand)
    print(f"[ETL] Registros de demanda extraídos: {len(demand_data.get('tabela', []))}")
    print(f"      kVA base por cliente: {demand_data.get('kva_por_cliente_base')}")
    print(f"      Plateau inicial (N≤{demand_data.get('plateau_inicial_ate_n_clientes')}): "
          f"Fator = {demand_data.get('plateau_fator')}")
    print(f"      Step linear por cliente (N>{demand_data.get('plateau_inicial_ate_n_clientes')}): "
          f"{demand_data.get('step_fator_diversificacao_por_cliente')}")
    print(f"      N máximo tabelado: {demand_data.get('n_max_tabelado')}")

    # ---- FATORES POR CLASSE ----
    ws_ramais = wb["Ramais"]
    class_factors = extract_class_factors(ws_ramais)
    print(f"[ETL] Classes de consumidores extraídas: {list(class_factors.keys())}")

    # ---- MONTAGEM DO JSON FINAL ----
    output = {
        "_metadata": {
            "fase": "21.3",
            "projeto": "CACL LIGHT",
            "fonte": XLSM_PATH,
            "descricao": "Curva de Demanda (Fator de Diversificação / Simultaneidade) da Light",
        },
        "curva_demanda_principal": demand_data,
        "fatores_por_classe_consumidor": class_factors,
    }

    with open(OUT_DEMAND, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[ETL] ✔ Gerado: {OUT_DEMAND}")

    # ---- ANÁLISE EXTRA: Verificar se R é uma fórmula ou tabela pura ----
    tabela = demand_data.get("tabela", [])
    print("\n[ANÁLISE DE PADRÃO]")
    print(f"  Primeiros 5 registros do Fator de Diversificação:")
    for row in tabela[:5]:
        print(f"    N={row['n_clientes']:>3}  FatorDiv={row['fator_diversificacao']:.4f}  Demanda={row['demanda_kva']:.2f} kVA")
    print(f"  ...")
    print(f"  Últimos 5 registros:")
    for row in tabela[-5:]:
        print(f"    N={row['n_clientes']:>3}  FatorDiv={row['fator_diversificacao']:.4f}  Demanda={row['demanda_kva']:.2f} kVA")

    step = demand_data.get("step_fator_diversificacao_por_cliente")
    plateau = demand_data.get("plateau_inicial_ate_n_clientes")
    fator0 = demand_data.get("plateau_fator")
    kva_base = demand_data.get("kva_por_cliente_base")

    print(f"\n[CONCLUSÃO] A curva de demanda é uma TABELA LINEAR PROGRESSIVA:")
    print(f"  Para N ≤ {plateau} clientes:  Demanda = {kva_base} × {fator0} = {round(kva_base * fator0, 4):.2f} kVA")
    print(f"  Para N > {plateau} clientes:  FatorDiv(N) = {fator0} + (N - {plateau}) × {step}")
    print(f"                              Demanda(N) = {kva_base} × FatorDiv(N) kVA")


if __name__ == "__main__":
    main()
