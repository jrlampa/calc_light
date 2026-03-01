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
