# CACL_LIGHT - Project Memory (RAG)

## Contexto do Projeto

O projeto **CACL_LIGHT** é um sistema web (React + FastAPI + SQLite3) projetado para substituir planilhas complexas de engenharia elétrica. O objetivo é realizar o cálculo de esforços mecânicos em postes de distribuição de energia, garantindo precisão idêntica à planilha original.

**Versão atual:** `0.20.0` (Fase 20 — Auditoria Final, Refatoração Pré-Deploy e Consolidação)

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
- `.dockerignore` → Exclui testes, __pycache__, .db, node_modules, dist, IDE files

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
