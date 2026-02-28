# Mapeamento estrito de células de entrada do modelo.xlsm
# Planilha alvo: "Ponto (1)" — apenas inputs brutos; cálculos ficam com a planilha.

CALC_SHEET = "Ponto (1)"

CELL_MAP: dict[str, str] = {
    # ── Cabeçalho ────────────────────────────────────────────────────────────
    "orgao":   "C1",   # Órgão (ex: "OMET")
    "projeto": "H1",   # Nome do projeto
    "ponto":   "K1",   # Número sequencial do ponto/poste
    "data":    "K3",   # Data do estudo (ISO 8601 string)
    # ── Dados do Poste ───────────────────────────────────────────────────────
    "tipo_poste":   "C7",   # Tipo do Poste (ex: "Concreto circular")
    "modelo_poste": "C8",   # Modelo do Poste (ex: "11 m / 300 daN")
    # ── MT 1º Nível – Tramo 1 ────────────────────────────────────────────────
    "mt1_t1_rede":   "C12",  # Tipo de rede (ex: "Compacta")
    "mt1_t1_cabo":   "C13",  # Tipo de cabo (ex: "1/0AWG-CAA, XLPE, 13,8 kV")
    "mt1_t1_vao":    "C14",  # Vão em metros
    "mt1_t1_flecha": "C15",  # Flecha em metros
    "mt1_t1_angulo": "C16",  # Ângulo em graus
    # ── MT 1º Nível – Alturas (comuns ao nível) ───────────────────────────────
    "mt1_altura_poste":     "C17",  # Altura do poste (m)
    "mt1_altura_ancoragem": "C18",  # Altura de ancoragem (m)
    # ── MT 1º Nível – Tramo 2 ────────────────────────────────────────────────
    "mt1_t2_rede":   "F12",
    "mt1_t2_cabo":   "F13",
    "mt1_t2_vao":    "F14",
    "mt1_t2_flecha": "F15",
    "mt1_t2_angulo": "F16",
    # ── MT 1º Nível – Tramo 3 ────────────────────────────────────────────────
    "mt1_t3_rede":   "I12",
    "mt1_t3_cabo":   "I13",
    "mt1_t3_vao":    "I14",
    "mt1_t3_flecha": "I15",
    "mt1_t3_angulo": "I16",
    # ── MT 1º Nível – Tramo 4 ────────────────────────────────────────────────
    "mt1_t4_rede":   "L12",
    "mt1_t4_cabo":   "L13",
    "mt1_t4_vao":    "L14",
    "mt1_t4_flecha": "L15",
    "mt1_t4_angulo": "L16",
    # ── MT 2º Nível – Tramo 1 ────────────────────────────────────────────────
    "mt2_t1_rede":   "C38",
    "mt2_t1_cabo":   "C39",
    "mt2_t1_vao":    "C40",
    "mt2_t1_flecha": "C41",
    "mt2_t1_angulo": "C42",
    # ── MT 2º Nível – Alturas ─────────────────────────────────────────────────
    "mt2_altura_poste":     "C43",
    "mt2_altura_ancoragem": "C44",
    # ── MT 2º Nível – Tramo 2 ────────────────────────────────────────────────
    "mt2_t2_rede":   "F38",
    "mt2_t2_cabo":   "F39",
    "mt2_t2_vao":    "F40",
    "mt2_t2_flecha": "F41",
    "mt2_t2_angulo": "F42",
    # ── MT 2º Nível – Tramo 3 ────────────────────────────────────────────────
    "mt2_t3_rede":   "I38",
    "mt2_t3_cabo":   "I39",
    "mt2_t3_vao":    "I40",
    "mt2_t3_flecha": "I41",
    "mt2_t3_angulo": "I42",
    # ── MT 2º Nível – Tramo 4 ────────────────────────────────────────────────
    "mt2_t4_rede":   "L38",
    "mt2_t4_cabo":   "L39",
    "mt2_t4_vao":    "L40",
    "mt2_t4_flecha": "L41",
    "mt2_t4_angulo": "L42",
    # ── BT – Tramo 1 ─────────────────────────────────────────────────────────
    "bt_t1_rede":   "C64",
    "bt_t1_cabo":   "C65",
    "bt_t1_vao":    "C66",
    "bt_t1_flecha": "C67",
    "bt_t1_angulo": "C68",
    # ── BT – Alturas ─────────────────────────────────────────────────────────
    "bt_altura_poste":     "C69",
    "bt_altura_ancoragem": "C70",
    # ── BT – Tramo 2 ─────────────────────────────────────────────────────────
    "bt_t2_rede":   "F64",
    "bt_t2_cabo":   "F65",
    "bt_t2_vao":    "F66",
    "bt_t2_flecha": "F67",
    "bt_t2_angulo": "F68",
    # ── BT – Tramo 3 ─────────────────────────────────────────────────────────
    "bt_t3_rede":   "I64",
    "bt_t3_cabo":   "I65",
    "bt_t3_vao":    "I66",
    "bt_t3_flecha": "I67",
    "bt_t3_angulo": "I68",
    # ── BT – Tramo 4 ─────────────────────────────────────────────────────────
    "bt_t4_rede":   "L64",
    "bt_t4_cabo":   "L65",
    "bt_t4_vao":    "L66",
    "bt_t4_flecha": "L67",
    "bt_t4_angulo": "L68",
}
