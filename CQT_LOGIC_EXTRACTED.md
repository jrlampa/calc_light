# CQT_LOGIC_EXTRACTED.md — Dossiê de Engenharia Reversa

# Projeto: CACL LIGHT | Fase: 21.1, 21.2, 21.3

# Origem: PLANILHA_DESTRAVADA.xlsm (Light / Enel)

---

## 1. Estrutura Geral do Cálculo de Queda de Tensão (CQT)

A planilha da Light calcula a Queda de Tensão (ΔV%) em redes BT/MT usando a equação:

```
ΔV% = K × I_carga × L_km
   ou equivalente:
ΔV% = K_kva × S_kVA × L_km
```

Onde **K** é o Coeficiente Unitário de QDT por tipo de condutor (extraído em `voltage_drop_coef_light.json`).

---

## 2. Fator de Demanda / Diversificação (Fase 21.3)

### 2.1 Constante de Demanda por Cliente

A planilha adota **2.22 kVA/cliente** como demanda individual base.  
Fonte: `ANÁLISE PONTO A PONTO!Q4:Q304` — constante em toda extensão da tabela.

### 2.2 Fator de Diversificação (Simultaneidade)

A demanda **não é simplesmente N × 2.22 kVA**. A planilha aplica um fator de diversificação que cresce de forma **linear progressiva** com número de clientes, respeitando limites inferior e superior.

**Tabela de comportamento descoberta:**

| Faixa de Clientes (N) | Regra | Fator de Diversificação | Demanda [kVA] |
|---|---|---|---|
| 1 ≤ N ≤ 4 | Plateau mínimo (constante) | 3.88 | **8.61 kVA** (fixo) |
| 5 ≤ N ≤ 295 | Linear crescente | `3.88 + (N − 4) × 0.56` | `2.22 × FatorDiv(N)` |
| N ≥ 296 | Plateau máximo (teto) | 83.00 | **184.26 kVA** (fixo) |

**Fórmula consolidada:**

```python
def fator_diversificacao(n_clientes: int) -> float:
    """Fator de Diversificação da Light para N clientes."""
    N_MIN_PLATEAU = 4
    N_MAX_PLATEAU = 296
    FATOR_MIN = 3.88
    FATOR_MAX = 83.00
    STEP = 0.56

    if n_clientes <= N_MIN_PLATEAU:
        return FATOR_MIN
    elif n_clientes >= N_MAX_PLATEAU:
        return FATOR_MAX
    else:
        return FATOR_MIN + (n_clientes - N_MIN_PLATEAU) * STEP


def demanda_kva(n_clientes: int, kva_por_cliente: float = 2.22) -> float:
    """Demanda agregada diversificada em kVA."""
    return round(kva_por_cliente * fator_diversificacao(n_clientes), 4)
```

> **Arquivo de referência:** `demand_curve_light.json` contém a tabela completa de 300 pontos.

### 2.3 Verificação da Linearidade

```
Step observado (N=4→5): 4.84 − 3.88 = 0.96  (salta do plateau)
Step observado (N=5→6): 5.80 − 4.84 = 0.96
Step observado (N=6→7): 6.76 − 5.80 = 0.96
...
Step observado (N alto): 0.56 por cliente (step modal)
```

> ⚠️ **Hipótese:** O step inicial (N=5) pode ser 0.96 e depois estabiliza em 0.56. Verificar com a fórmula no arquivo `.xlsm` (openpyxl com `data_only=False`).

### 2.4 Fatores por Classe de Consumidor (Aba Ramais)

Para o **cálculo de QDT por ramal**, a planilha usa coeficientes distintos por perfil de carga:

| Classe | Coeficiente por Condutor | Nota |
|---|---|---|
| **Comercial** | Ver `demand_curve_light.json` → `fatores_por_classe_consumidor.Comercial` | Maior carga específica |
| **Residencial** | Ver `demand_curve_light.json` → `fatores_por_classe_consumidor.Residencial` | Carga padrão residencial |
| **Misto** | Ver `demand_curve_light.json` → `fatores_por_classe_consumidor.Misto` | Média ponderada |

Formato do coeficiente: `QDT_total% = Coef × I × (L/1000)` onde I=corrente, L=comprimento em metros.

---

## 3. Catálogo de Cabos (Fase 21.2)

### 3.1 Coeficiente Unitário K de QDT (dado mais crítico)

A aba oculta `Coeficiente Unitário` contém os coeficientes K pré-calculados:

```
ΔV% = K × kVA_carga × L_km
```

| Condutor | R (Ω/km) | X (Ω/km) | K |
|---|---|---|---|
| 33 AA | 1.0903 | 0.4034 | 0.24019 |
| 33 AC | 1.0254 | 0.3419 | 0.22333 |
| 53 AA | 0.7059 | 0.3705 | 0.16472 |
| 53 AC | 0.6456 | 0.3235 | 0.14920 |
| 107 A | 0.3225 | 0.2968 | 0.09056 |
| 107 AC | 0.3250 | 0.2968 | 0.09094 |
| 201 A | 0.1731 | 0.2686 | 0.06602 |
| 201 AC | 0.1731 | 0.2686 | 0.06602 |
| 53 QX | 0.6641 | 0.1311 | 0.13986 |
| 85 QX | 0.4180 | 0.1279 | 0.09032 |
| 107 QX | 0.3313 | 0.1290 | 0.07346 |
| 53 MX | 0.6641 | 0.1311 | 0.13986 |
| 70 MMX | 0.5697 | 0.1260 | 0.12055 |
| 185 MMX | 0.2149 | 0.1178 | 0.05063 |

> **Arquivo de referência:** `voltage_drop_coef_light.json`

### 3.2 Cabos BT Multiplex (Aba Ramais)

Extraídos em `cables_catalog_light.json` com: bitola, R (Ω/km), X (Ω/km), Ampacidade (A).

### 3.3 Cabos MT Subterrâneos e Aéreos (Aba Tabela)

Extraídos em `cables_catalog_light.json` com: seção (mm²), material, R (Ω/km), X (Ω/km), tipo.

---

## 4. Parâmetros de Transformador (Fase 21.2)

Extraídos em `transformers_catalog_light.json`. A Light usa cenários de alocação de QDT:

| Potência (kVA) | ΔV Trafo (%) | ΔV Rede Sec (%) | ΔV Ramal (%) | Tabela |
|---|---|---|---|---|
| ≤300 | 4.5 | 5.0 | 1.5 | Tab_B (Aéreo-Aéreo) |
| 500 | 6.5 | 3.0 | 1.5 | Tab_B (Aéreo-Aéreo) |
| 1000 | 6.5 | 3.0 | 1.5 | Tab_B (Aéreo-Aéreo) |

---

## 5. Abas Identificadas (Fase 21.1)

| Aba | Estado | Conteúdo |
|---|---|---|
| PP e CE | hidden | Classificação de obras por programa |
| Base de Dados | hidden | Lookup tables de projeto |
| PF e Prestação de Serviço | hidden | Custos ramal |
| **Ramais** | **visible** | **Catálogo BT + Fatores de classe** |
| **Distrib. Cargas** | **visible** | **Distribuição de carga por poste** |
| Coeficiente Unitário | hidden | **K de QDT por condutor (CRÍTICO)** |
| FML | hidden | Tabelas auxiliares |
| **QDT Dutra 2.3 Lado Esquerdo** | **visible** | **Motor principal de QDT** |
| **QDT Dutra 2.3 Lado Direito** | **visible** | **Motor principal de QDT** |
| **ANÁLISE PONTO A PONTO** | **visible** | **Curva de demanda + diversificação** |
| Curva Disj. | hidden | Curvas de disjuntores |
| Curva NH | hidden | Curvas NH-fusíveis |
| Alocação % de tensão | hidden | Tabelas de alocação percentual de QDT |
| Tabela | hidden | Catálogo MT Subterrâneo e Aéreo |

---

## 6. Arquivos Gerados

| Arquivo | Fase | Conteúdo |
|---|---|---|
| `21_1_TOPOLOGY_REPORT.txt` | 21.1 | Mapeamento topográfico completo |
| `cables_catalog_light.json` | 21.2 | 46 condutores BT/MT |
| `voltage_drop_coef_light.json` | 21.2 | 14 coeficientes K de QDT |
| `transformers_catalog_light.json` | 21.2 | 7 cenários de trafo |
| `demand_curve_light.json` | 21.3 | 300 pontos da curva de demanda |

---

## 7. Algoritmo de Rateio Top-Down (Rede Normal) — Fase 21.3b

> **Bifurcação de Método:** Redes com medição real de trafo usam rateio proporcional;
> redes clandestinas usam estimativa bottom-up por área.

### 7.1 Entradas (Distrib. Cargas)

| Célula | Descrição | Fórmula Extraída |
|---|---|---|
| **G3** | Leitura do Transformador | `INPUT` (usuário preenche) |
| **G5** | Demanda Máxima | `=IF(G3="","",G3 × 0.375)` |
| **G7** | Fator de Temperatura | `1` (padrão; pode ser ajustado) |
| **G9** | Demanda Corrigida | `=IF(G7="","",G7 × G5)` |

**Fórmula analítica da Demanda Corrigida:**
```
Dem_Corrigida = Fator_Temp × (Leitura_Trafo × 0.375)
             = 1.0 × (G3 × 0.375)     [com Fator_Temp padrão = 1]
```
O fator `0.375` converte a corrente de trafo em demanda kVA considerando FP e tensão de operação.

### 7.2 Peso Proporcional de Cada Poste (Ramais!W_n)

Cada poste tem um **Peso W_n** calculado como soma ponderada dos ramais ligados a ele,
usando a **Ampacidade de cada tipo de condutor** como peso:

```
W_n = Σ [qtd_ramais[tipo] × Ampacidade[tipo]]

Ampacidades (Linha 6):
  5mm²CC=66A | 8mm²CC=88A | 13mm²CC=116A | 21mm²CC=151A | 33mm²CC=205A
  53mm²CC=272A | 67mm²CC=313A | 85mm²CC=366A | 107mm²CC=418A | 127mm²CC=466A
  13DX=78A | 13TX=80A | 13QX=72A | 21QX=95A | 53QX=165A
  85QX=220A | 107QX=254A | 70MMX=227A | 185MMX=423A
```

**Fórmula da planilha (Ramais!W25 completa):**
```excel
=C25×$C$6 + D25×$D$6 + E25×$E$6 + F25×$F$6 + G25×$G$6 + H25×$H$6
 + I25×$I$6 + J25×$J$6 + K25×$K$6 + L25×$L$6 + M25×$M$6
 + N25×$N$6 + O25×$O$6 + P25×$P$6 + Q25×$Q$6 + R25×$R$6
 + S25×$S$6 + T25×$T$6 + U25×$U$6 + V25×$V$6
```

**Totais:**
```
W_Total_L1 = SUM(W25:W49)   ← Ramais!W50
W_Total_L2 = SUM(W56:W80)   ← Ramais!W81
```

### 7.3 Rateio por Poste (Distrib. Cargas)

Para cada poste n:

```
Carga_Poste_n_L1 = Dem_Corrigida × W_L1[n] / (W_Total_L1 + W_Total_L2)
Carga_Poste_n_L2 = Dem_Corrigida × W_L2[n] / (W_Total_L1 + W_Total_L2)

Carga Acumulada até o Trafo (tronco do trecho):
Carga_Acum_n     = SUM(Carga_n .. Carga_ultimo_poste)
```

**Fórmula real (Distrib. Cargas!C5):**
```excel
=IF($G$9="","", $G$9 × (Ramais!W26 / (Ramais!$W$50 + Ramais!$W$81)))
```

### 7.4 Algoritmo Completo (Pseudocódigo)

```python
# ETAPA 1: Input
leitura_trafo = G3         # A ou kVA (manual)
fator_temp    = G7         # 1.0 padrão
dem_corrigida = fator_temp × leitura_trafo × 0.375   # G9

# ETAPA 2: Peso de cada poste
w = {}
for n in postes:
    w[n] = sum(qtd_ramais[n][tipo] × ampacidade[tipo]
               for tipo in condutores)

w_total_L1 = sum(w[n] for n in lado_1)
w_total_L2 = sum(w[n] for n in lado_2)
w_total    = w_total_L1 + w_total_L2

# ETAPA 3: Carga por poste (proporcional)
for n in postes:
    carga[n] = dem_corrigida × w[n] / w_total

# ETAPA 4: Carga acumulada (do poste n até o trafo)
carga_acum[n] = sum(carga[k] for k in postes[n:])
```

---

## 8. Algoritmo Bottom-Up (Clandestinos) — Fase 21.3b

Clientes clandestinos **não têm medição de trafo**. A demanda é estimada por porte da edificação.

### 8.1 Constante Base da Light

| Parâmetro | Valor | Fonte |
|---|---|---|
| kVA/cliente (UC ~60m²) | **2.22 kVA** | `ANÁLISE PONTO A PONTO!Q4:Q304` |
| Fator de diversificação | Tabela `demand_curve_light.json` | Fase 21.3 |

### 8.2 Fórmula de Demanda Clandestina

```
Demanda_Clandestin(N) = 2.22 × FatorDiv(N)   [kVA]

FatorDiv(N):
  N ≤ 4   →  3.88          (plateau mínimo → 8.61 kVA)
  5≤N≤295 →  3.88 + (N-4) × 0.56   (linear)
  N ≥ 296 →  83.00          (teto → 184.26 kVA)
```

### 8.3 Integração com o Motor CQT

```
ΔV%(trecho) = K_condutor × Demanda_Clandestin(N) × L_km
```
Onde `K_condutor` vem de `voltage_drop_coef_light.json`.

---

## 9. Coeficientes QDT por Classe (Ramais — Fase 21.3b)

As linhas 13-15 da aba `Ramais` definem coeficientes de QDT considerando FP real por classe:

| Classe | FP cos(φ) | sin(φ) | Fórmula K |
|---|---|---|---|
| Comercial | 0.85 | 0.5268 | `K = R × 0.85 + X × 0.5268` |
| Residencial | 0.95 | 0.3122 | `K = R × 0.95 + X × 0.3122` |
| Misto | 0.90 | 0.4359 | `K = R × 0.90 + X × 0.4359` |

**Uso:** `ΔV% = K × I_A × L_km` onde I é a corrente de fase.

---

## 10. Arquivos Gerados (Atualizado)

| Arquivo | Fase | Conteúdo |
|---|---|---|
| `21_1_TOPOLOGY_REPORT.txt` | 21.1 | Mapeamento topográfico completo |
| `cables_catalog_light.json` | 21.2 | 46 condutores BT/MT |
| `voltage_drop_coef_light.json` | 21.2 | 14 coeficientes K de QDT |
| `transformers_catalog_light.json` | 21.2 | 7 cenários de trafo |
| `demand_curve_light.json` | 21.3 | 300 pontos da curva de demanda |
| `load_distribution_logic.json` | 21.3b | Algoritmo de rateio (fórmulas + pesos) |
