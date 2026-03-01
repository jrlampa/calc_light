# CACL_LIGHT - Project Memory (RAG)

## Contexto do Projeto

O projeto **CACL_LIGHT** é um sistema web (React + FastAPI + SQLite3) projetado para substituir planilhas complexas de engenharia elétrica. O objetivo é realizar o cálculo de esforços mecânicos em postes de distribuição de energia, garantindo precisão idêntica à planilha original.

**Versão atual:** `0.21.0` (Fase 21 — Infraestrutura de Uso Diário Local / Local Production)

## Regras e Arquitetura (Não Negociáveis)

1. **Branch:** Apenas `dev`.
2. **Sem dados mockados:** Tudo deve vir do banco de dados SQLite3 ou ser calculado dinamicamente.
3. **Visão (UI):** 2.5D (não usar 3D puro), com design Glassmorphism, pt-BR e focado em ser idêntico à interface da planilha original.
4. **Arquitetura (DDD):**
   - **Smart Backend:** Python FastAPI com as regras de negócio bem isoladas (`domain`), recebendo e devolvendo DTOs.
   - **Thin Frontend:** React + Vite, responsável apenas por renderizar o estado e enviar comandos.
5. **Boas Práticas:** Modularidade, Responsabilidade Única (Regra dos 500 linhas), Segurança (Sanitização) e Clean Code.
6. **Zero Custo:** Uso exclusivo de APIs e bibliotecas públicas gratuitas.
7. **Testes:** 100% de cobertura nos 20% críticos (`domain/`) e >80% no restante. Testes Unitários e E2E.
8. **Infraestrutura:** Docker First (multi-stage Dockerfile, `docker-compose.yml`, `.dockerignore` atualizados).
9. **BIM:** Half-way BIM na modelagem relacional dos postes e equipamentos.

## Árvore de Pastas Padronizada (Fase 20)

```
calc_light/
├── MEMORY.md                          ← RAG do projeto (este arquivo)
├── .dockerignore                      ← Excluí testes, __pycache__, .db, node_modules
├── docker-compose.yml                 ← Prod: healthcheck, named volume db_data, nginx frontend
├── backend/
│   ├── Dockerfile                     ← Multi-stage (builder + runner non-root)
│   ├── requirements.txt
│   └── app/
│       ├── main.py                    ← FastAPI entry-point; APP_VERSION = "0.20.0"
│       ├── templates/
│       │   └── modelo.xlsm            ← Planilha modelo (keep_vba=True)
│       ├── domain/
│       │   ├── calculators.py         ← 100% cov; extra_drag_area_m2 (Fase 19)
│       │   ├── excel_exporter.py      ← 100% cov
│       │   ├── excel_mapping.py       ← 100% cov
│       │   ├── gis_parser.py          ← 100% cov
│       │   ├── models.py              ← 100% cov; CatalogEquipment (Fase 19)
│       │   ├── solver.py              ← 100% cov
│       │   └── topology_service.py    ← 100% cov (Fase 20: target_node paths cobertos)
│       ├── api/
│       │   └── routers/
│       │       ├── catalogs.py        ← GET /catalogs/equipment (Fase 19)
│       │       ├── gis.py             ← >80% cov (Fase 20: test_gis_api.py)
│       │       ├── projects.py        ← PATCH settings, GET/PUT node equipment (Fase 19)
│       │       ├── solver.py          ← 100% cov
│       │       ├── topology.py        ← 100% cov
│       │       ├── calculations.py
│       │       ├── forces.py
│       │       └── dependencies.py
│       ├── api/services/
│       │   └── topology_service.py    ← Lê enable_equipment_drag, agrega áreas por nó
│       ├── infrastructure/database/
│       │   ├── database.py            ← _apply_migrations() idempotentes; seed equipamentos
│       │   └── repository.py          ← update_project_settings, get_equipment_catalog,
│       │                                 get/set_node_equipment_ids, get_node_equipment_total_area
│       ├── schemas/
│       │   ├── projects.py            ← enable_equipment_drag, ProjectSettingsUpdate, NodeEquipmentUpdate
│       │   ├── catalogs.py            ← CatalogEquipmentResponse
│       │   ├── gis.py
│       │   └── topology.py
│       └── tests/
│           ├── test_api.py
│           ├── test_equipment_drag.py ← 18 testes (Fase 19): calculators, topology, repo, API
│           ├── test_gis_api.py        ← 13 testes (Fase 20): parse-file, import-nodes, outgoing-conductors
│           ├── test_ghost_node.py     ← 20 testes paranóicos ghost node
│           ├── test_solver.py         ← 15 testes (100% cov em solver.py)
│           ├── test_gis_parser.py     ← 100% cov em gis_parser.py
│           ├── test_graph_inheritance.py
│           ├── test_excel_export.py
│           ├── test_calculators.py
│           ├── test_database.py
│           ├── test_topology.py       ← Fase 20: target_node force vectors cobertos
│           └── test_auditor.py
├── frontend/
│   ├── Dockerfile                     ← Dev (node:18-alpine)
│   ├── Dockerfile.prod                ← Prod multi-stage (node:20-alpine + nginx:1.27-alpine)
│   ├── nginx.conf
│   ├── package.json
│   └── src/
│       ├── api.ts
│       ├── App.tsx                    ← <500 linhas (Fase 20): usa NewProjectModal + ProjectSidebar
│       ├── store.ts                   ← useTopologyHistoryStore (zundo), useUIStore
│       ├── hooks/
│       │   ├── useCatalogs.ts         ← poles, conductors, equipment (Fase 19)
│       │   └── useProjects.ts         ← useProjectSettings, useUpdateProjectSettings,
│       │                                 useNodeEquipment, useSetNodeEquipment (Fase 19)
│       └── components/
│           ├── App.tsx-components:    ← Extraídos na Fase 20 (SRP):
│           ├── NewProjectModal.tsx    ← Modal de criação de projeto
│           ├── ProjectSidebar.tsx     ← Sidebar com lista de projetos
│           ├── TopologyDiagram.tsx    ← <500 linhas (Fase 20): wrapper + GIS + Solver modais
│           ├── TopologyCanvas.tsx     ← Extraído (Fase 20): ReactFlow canvas, undo/redo, drag, nudge
│           ├── TractionCalculator.tsx ← <500 linhas (Fase 20): usa ProjectSettingsPanel + NodeEquipmentSelector
│           ├── ProjectSettingsPanel.tsx ← Toggle enable_equipment_drag iOS-style (Fase 19-20)
│           ├── NodeEquipmentSelector.tsx ← Pill multi-select de equipamentos por nó (Fase 19-20)
│           ├── CustomNode.tsx
│           ├── CustomEdge.tsx
│           ├── ForceDiagram.tsx
│           ├── GisImportModal.tsx
│           ├── GhostNodeModal.tsx
│           ├── SolverModal.tsx
│           ├── ExportButton.tsx
│           ├── Layout.tsx
│           ├── RecoveryModal.tsx
│           └── ShortcutsModal.tsx
└── database/
```

## Domínio de Negócio (Cálculo de Tração)

A lógica principal de cálculo envolve Níveis (MT1, MT2, BT, Ramais) e Tramos (T1 a T4). As fórmulas extraídas da planilha são:

- **Tração dos Condutores (daN):** `(Peso_Total * Vão^2) / (8 * Flecha)`
- **Vento (daN):** `Força_Vento_X = Pressão_Vento * (Vão/2) * Diâmetro_Total * COS(Ângulo)`
- **Decomposição:** Tração decomposta em `Compx` e `Compy` de acordo com o ângulo do vão.
- **Resultante por Nível:** Soma vetorial das trações + Soma vetorial das forças de vento.
- **Resultante aplicada ao Poste:** Ajustada pelos momentos de alavanca (Altura Ancoragem / Altura Útil do Poste).

## Fase 19 — Catálogo de Equipamentos e Arrasto Adicional (opt-in)

Na física real, equipamentos acoplados ao poste (Transformadores, Cruzetas, Chaves) adicionam área
de arrasto significativa contra o vento. A concessionária Enel/Light NÃO exige esse rigor no cálculo
padrão. Portanto, é tratado como "Modo Avançado" 100% opcional (Opt-in) por projeto.

### Flag `enable_equipment_drag`

- **Tabela:** `projects.enable_equipment_drag INTEGER DEFAULT 0`
- **Migração:** `_apply_migrations()` idempotente em `database.py`
- **Endpoint:** `PATCH /projects/{id}/settings` → `{"enable_equipment_drag": true|false}`

### Catálogo Estático `catalog_equipment`

| Nome | Área Arrasto (m²) |
|---|---|
| Trafo 45 kVA | 0.85 |
| Trafo 75 kVA | 1.05 |
| Trafo 112,5 kVA | 1.25 |
| Cruzeta Polimérica 2,0 m | 0.30 |
| Cruzeta Metálica 2,4 m | 0.40 |
| Chave Faca MT | 0.15 |
| Chave a Óleo MT | 0.20 |

### Tabela `node_equipment` (join)

`(node_id, equipment_id)` — PRIMARY KEY composta, CASCADE DELETE.

### Motor Matemático Condicional (`calculators.py`)

- `calculate_level_resultant(inputs, conductors, extra_drag_area_m2=0.0)`
- Quando `enable_equipment_drag=False`: `extra_drag_area_m2` é sempre 0 (padrão Enel)
- Quando `enable_equipment_drag=True`: `extra_drag_area_m2 = soma das áreas dos equipamentos do nó`
- Aplicado apenas no primeiro nível (representa o poste uma única vez)
- Conversão: `equipament_wind_area = area / (span_m / 2)` → somado ao diâmetro do poste

### API Fase 19

| Rota | Método | Descrição |
|---|---|---|
| `GET /catalogs/equipment` | GET | Catálogo estático de equipamentos |
| `PATCH /projects/{id}/settings` | PATCH | Toggle enable_equipment_drag |
| `GET /projects/{id}/nodes/{nid}/equipment` | GET | IDs de equipamentos acoplados ao nó |
| `PUT /projects/{id}/nodes/{nid}/equipment` | PUT | Substitui lista de equipamentos do nó |

### Frontend Fase 19

- **`ProjectSettingsPanel.tsx`** — Toggle iOS-style + tooltip "Ative apenas se exigido pela concessionária..."
- **`NodeEquipmentSelector.tsx`** — Pill multi-select por nó; mostra área total acumulada
- Nós na lista clicáveis quando modo avançado ativo → abre seletor de equipamentos

## Fase 17 — Solver Global / Motor de Otimização

### Algoritmo (solver.py → run_solver)

```
Para cada nó REAL (is_ghost=False):
  1. Calcula esforço atual via _compute_effort()
  2. threshold = min(nominal_capacity, 2000 daN)
  3. Se esforço <= threshold → poste OK, skip
  4. Se sobrecarregado:
     a. Range padrão (0.3–0.9 m) → SolverSuggestion(is_extreme=False)
     b. Range extremo (1.0–1.3 m) → SolverSuggestion(is_extreme=True)
     c. Nada funcionar → SolverSuggestion(requires_span_break=True)
```

## Nó Fantasma (Ghost Node)

- **Flag:** `project_nodes.is_ghost INTEGER DEFAULT 0`
- Ghost contribui com tração no nó real via vão compartilhado
- Ghost NÃO tem `effort_dan`, `utilization_percent`, `is_overloaded` calculados (todos 0/False)
- Ghost aparece no diagrama (borda tracejada, opacidade 50%, sem badge de esforço)
- **API:** `PATCH /projects/{id}/nodes/{nid}/ghost` → `{"is_ghost": true|false}`
- Export Excel filtra `is_ghost=True` (ghost não entra no ZIP)

## Fase 18 — Zero Data Loss (Auto-Save / Undo-Redo / Disaster Recovery)

- **Auto-save:** `localStorage.setItem('cacl_backup_{id}', JSON)` debounced 1.5s após mudança
- **Undo/Redo:** `zundo` temporal middleware no `useTopologyHistoryStore`, limite=50
- **Hotkeys:** `Ctrl+Z` (undo), `Ctrl+Y` / `Ctrl+Shift+Z` (redo)
- **Disaster Recovery:** `RecoveryModal` — ao abrir projeto compara `localStorage.savedAt` vs servidor

## Fase 20 — Auditoria Final e Consolidação

### Regra dos 500 Linhas — Arquivos Refatorados

| Arquivo | Antes | Depois | Extraídos |
|---|---|---|---|
| `App.tsx` | 508 | 413 | `NewProjectModal.tsx`, `ProjectSidebar.tsx` |
| `TractionCalculator.tsx` | 521 | 368 | `ProjectSettingsPanel.tsx`, `NodeEquipmentSelector.tsx` |
| `TopologyDiagram.tsx` | 561 | 120 | `TopologyCanvas.tsx` |

### Cobertura de Testes (Pareto 80/20)

| Camada | Cobertura |
|---|---|
| `domain/calculators.py` | **100%** |
| `domain/excel_exporter.py` | **100%** |
| `domain/gis_parser.py` | **100%** |
| `domain/solver.py` | **100%** |
| `domain/models.py` | **100%** |
| `domain/topology_service.py` | **100%** (Fase 20: target_node paths) |
| Total domain | **98%+ → 100%** |
| `api/routers/gis.py` | **~37% → >80%** (Fase 20: `test_gis_api.py`) |
| Aplicação completa | **94%+** |

### Docker Ecosystem

- `backend/Dockerfile` → Multi-stage (builder + runner), non-root user `app`
- `frontend/Dockerfile.prod` → Multi-stage (node:20-alpine build + nginx:1.27-alpine serve)
- `docker-compose.yml` → Healthcheck backend, `named volume db_data`, nginx frontend na porta 80
- `.dockerignore` → Exclui testes, **pycache**, .db, node_modules, dist, IDE files

## GIS Parser

- **Formatos suportados:** `.kml`, `.kmz`, `.geojson`, `.json`, `.xlsx`, `.xls`
- **Zero dependências C++:** usa apenas stdlib + `openpyxl`

## Motor de Exportação em Lotes (excel_exporter.py)

- **`BATCH_SIZE = 30`**: máximo de arquivos por lote.
- **`build_poste_xlsm(data, template_path)`**: gera bytes de um único `.xlsm`.
- **`build_export_zip(postes_data, template_path)`**: gera ZIP mestre em lotes.
- **Endpoint:** `GET /projects/{id}/export/excel` → `application/zip`.

## Equipe (Roles)

- **Tech Lead:** Orquestração geral do plano.
- **Dev Fullstack Sênior:** Codificação principal (Python/React).
- **DevOps/QA:** Garantia de testes, dockerização e cobertura de código.
- **UI/UX Designer:** Reproduzir a interface da planilha no modelo 2.5D.
- **Estagiário (Criatividade):** Soluções fora da caixa para problemas não mapeados.

---

## Fase 21 — Manual de Operação Local (Local Production)

**Versão:** `0.21.0` | **Papel:** Engenheiro DevOps / SRE / DevEx

Esta fase configura o ambiente de **uso diário local** do CACL LIGHT com infraestrutura
de 1 clique, Chrome App Mode (interface de aplicativo nativo), persistência blindada do
banco de dados, backup automático e workflow de atualização para o desenvolvedor ativo.

### Estrutura de Arquivos de Operação

```
calc_light/
├── docker-compose.local.yml     ← Compose para produção local (bind-mounts + log limits + sqlite-web)
├── iniciar.sh / iniciar.bat     ← One-click: sobe containers, healthcheck loop, abre Chrome App
├── parar.sh  / parar.bat        ← Backup automático + parada graciosa
├── atualizar.sh / atualizar.bat ← git pull + rebuild + restart (preservando dados)
├── backup_db.sh / backup_db.bat ← Backup manual com timestamp
├── local_data/
│   ├── db/
│   │   └── cacl_light.db        ← Banco SQLite (persistido no host, nunca no container)
│   └── templates/
│       └── modelo.xlsm          ← Template Excel (persistido no host)
└── backups/
    └── cacl_backup_YYYY-MM-DD_HH-MM-SS.db  ← Backups automáticos com timestamp
```

### Como Iniciar o Sistema (One-Click Start)

**Linux / macOS:**

```bash
# Na primeira vez, tornar os scripts executáveis:
chmod +x iniciar.sh parar.sh atualizar.sh backup_db.sh

# Iniciar:
./iniciar.sh
```

**Windows:**

```
Duplo-clique em: iniciar.bat
```

O script automaticamente:

1. Cria as pastas `local_data/db/`, `local_data/templates/` e `backups/` se não existirem
2. Copia `backend/app/templates/modelo.xlsm` → `local_data/templates/` (apenas na 1ª vez)
3. Executa `docker compose -f docker-compose.local.yml up -d --build`
4. **Aguarda o sistema responder HTTP 200** (healthcheck loop — máx 90s, testa a cada 3s)
5. **Abre o Chrome em modo App** (`--app=http://localhost`) — janela dedicada sem barra de navegação
   - Fallback automático para o navegador padrão se Chrome não estiver instalado

### Como Parar o Sistema (com Backup Automático)

**Linux / macOS:**

```bash
./parar.sh
```

**Windows:**

```
Duplo-clique em: parar.bat
```

`parar` realiza automaticamente um backup com timestamp **antes** de derrubar os containers,
protegendo contra corrupção acidental na parada do sistema.

### Como Atualizar o Sistema (Developer Workflow)

Quando houver novos commits no repositório:

**Linux / macOS:**

```bash
./atualizar.sh
```

**Windows:**

```
Duplo-clique em: atualizar.bat
```

O script `atualizar` realiza:

1. **Backup pré-atualização** — salvo com sufixo `_pre-update_` em `./backups/`
2. **`git pull`** — baixa as últimas alterações
3. **`docker compose build`** — reconstrói as imagens com o novo código
4. **`docker compose up -d`** — reinicia os serviços (volumes de dados preservados)
5. **Healthcheck loop** — aguarda o sistema responder antes de finalizar

### Como Fazer Backup Manual

**Linux / macOS:**

```bash
./backup_db.sh
```

**Windows:**

```
Duplo-clique em: backup_db.bat
```

Cria `./backups/cacl_backup_YYYY-MM-DD_HH-MM-SS.db`. O script Linux auto-purga mantendo
os **30 backups mais recentes**.

### Como Restaurar um Backup (Disaster Recovery)

1. **Parar o sistema:**

   ```bash
   ./parar.sh        # Linux / macOS
   # parar.bat       # Windows
   ```

2. **Substituir o banco pelo backup desejado:**

   ```bash
   # Linux / macOS:
   cp backups/cacl_backup_2026-03-01_14-30-05.db local_data/db/cacl_light.db

   # Windows (Prompt de Comando):
   copy backups\cacl_backup_2026-03-01_14-30-05.db local_data\db\cacl_light.db
   ```

3. **Reiniciar:**

   ```bash
   ./iniciar.sh      # Linux / macOS
   # iniciar.bat     # Windows
   ```

### Visualizador SQLite (sqlite-web) — Inspeção do Banco

O `docker-compose.local.yml` inclui o serviço `sqlite-web` (imagem `coleifer/sqlite-web`),
que permite **inspecionar o banco de dados diretamente no navegador** sem instalar nenhum
software extra.

| Ação | URL |
|---|---|
| Visualizar tabelas e dados | **<http://localhost:8080>** |

- O banco é montado em **modo leitura** (`:ro`) — sem risco de alteração acidental
- Logs limitados a `5m / 2 arquivos` para não lotar o HD

### Persistência de Dados (Regra de Ouro)

| Dado | Caminho no Host | Caminho no Container |
|---|---|---|
| Banco SQLite | `./local_data/db/cacl_light.db` | `/database/cacl_light.db` |
| Template Excel | `./local_data/templates/modelo.xlsm` | `/app/app/templates/modelo.xlsm` |

O `docker-compose.local.yml` usa **bind-mounts** (não named volumes) para garantir que
os arquivos sejam visíveis e editáveis diretamente no sistema operacional.

### Limites de Log (Proteção de HD)

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"   # Máximo 10 MB por arquivo de log
    max-file: "3"     # Máximo 3 arquivos rotativos = 30 MB total por container
# sqlite-web: max-size 5m / max-file 2
```

### Acesso à Interface

| Serviço | URL | Descrição |
|---|---|---|
| Aplicação CACL LIGHT | <http://localhost> | Frontend React via Nginx |
| API Backend | <http://localhost:8000/docs> | FastAPI Swagger docs |
| Health Check | <http://localhost:8000/health> | Status do backend |
| Visualizador SQLite | <http://localhost:8080> | sqlite-web (read-only) |

---

## Fase 21.1 — Mapeamento Topográfico (Engenharia Reversa)

**Objetivo:** Mapear a estrutura da `PLANILHA_DESTRAVADA.xlsm` para identificar abas de catálogo, nomes definidos e coordenadas de dados estáticos.

### Ferramentas de Mineração

- `miner_21_1_topology.py`: Script exploratory usando `openpyxl` para extrair metadados e localizar catálogos via heurística de palavras-chave.
- `21_1_TOPOLOGY_REPORT.txt`: Relatório gerado contendo o dicionário de Named Ranges e coordenadas das abas.

### Descobertas Iniciais

- O mapeamento foca em dados de cabos (Resistência, Reatância, Ampacidade) e transformadores (kVA).
- O script identifica o estado de visibilidade das abas (Visible, Hidden, VeryHidden) para localizar tabelas "escondidas" pela Light.

---

## Fase 21.2 — ETL de Catálogos Elétricos (Light)

**Script:** `miner_21_2_catalogs.py` | **Branch:** `feature/cqt-mining`

### Fontes de Dados Extraídas

| Aba (xlsm) | Estado | Conteúdo |
|---|---|---|
| Ramais | visible | Condutores BT multiplex: R, X, Ampacidade |
| Tabela | hidden | Cabos BT rede + Cabos MT Subterrâneo e Aéreo |
| Coeficiente Unitário | hidden | **CRÍTICO**: coef K → dV% = K × kVA × L_km |
| Alocação % de tensão | hidden | Cenários de QDT por trafo (Tab_B, Tab_C, Tab_D) |

### JSONs Gerados (Seeders para Fase 22)

| Arquivo | Registros | Uso |
|---|---|---|
| cables_catalog_light.json | 46 | Catálogo de cabos BT/MT |
| voltage_drop_coef_light.json | 14 | Coeficiente K de QDT por condutor (crítico para CQT) |
| transformers_catalog_light.json | 7 | Cenários de QDT por trafo |

### Schema cables_catalog_light.json
```json
{
  "source": "Ramais | Tabela",
  "voltage_level": "BT | MT",
  "conductor_name": "53 QX",
  "section_mm2": null,
  "material": "Al | Cu | CC",
  "r_ohm_per_km": 0.6641,
  "x_ohm_per_km": 0.1311,
  "ampacity_a": null,
  "conductor_type": "multiplex_aerial | network | underground | aerial"
}
```

### Schema voltage_drop_coef_light.json (CRÍTICO para CQT)
```json
{
  "source": "Coeficiente Unitário",
  "conductor_name": "53 QX",
  "r_ohm_per_km": 0.6641,
  "x_ohm_per_km": 0.1311,
  "voltage_drop_coef_k": 0.13985879198405582
}
```
> **Fórmula:** dV% = K × kVA_carga × L_km

### Schema transformers_catalog_light.json
```json
{
  "source": "Alocação % de tensão",
  "tabela": "Tab_B_Aereo-Aereo",
  "power_kva": 300.0,
  "coincidence_factor_pct": 75.0,
  "primary_voltage_v": 13200.0,
  "secondary_voltage_v": 220.0,
  "dv_primary_pct": 3.5,
  "dv_transformer_pct": 4.5,
  "dv_secondary_pct": 5.0,
  "dv_branch_pct": 1.5
}
```
