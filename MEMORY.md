# CACL_LIGHT - Project Memory (RAG)

## Contexto do Projeto

O projeto **CACL_LIGHT** é um sistema web (React + FastAPI + SQLite3) projetado para substituir planilhas complexas de engenharia elétrica (como "CÁLCULO DE TRAÇÃO OII-25-2249.xlsm" e "POSTE69.xlsm"). O objetivo é realizar o cálculo de esforços mecânicos em postes de distribuição de energia, garantindo precisão idêntica à planilha original.

**Versão atual:** `0.16.1` (Fase 16.1 — Nó Fantasma / Ghost Node)

## Regras e Arquitetura (Não Negociáveis)

1. **Branch:** Apenas `dev`.
2. **Sem dados mockados:** Tudo deve vir do banco de dados SQLite3 ou ser calculado dinamicamente.
3. **Visão (UI):** 2.5D (não usar 3D puro), com design Glassmorphism, pt-BR e focado em ser idêntico à interface da planilha original.
4. **Arquitetura (DDD):**
   - **Smart Backend:** Python FastAPI com as regras de negócio bem isoladas (`domain`), recebendo e devolvendo DTOs.
   - **Thin Frontend:** React + Vite, responsável apenas por renderizar o estado e enviar comandos.
5. **Boas Práticas:** Modularidade, Responsabilidade Única, Segurança (Sanitização) e Clean Code.
6. **Zero Custo:** Uso exclusivo de APIs e bibliotecas públicas gratuitas.
7. **Testes:** 100% de cobertura nos 20% críticos (cálculos de tração) e >80% no restante. Testes Unitários e E2E. Execução sempre que julgar necessário.
8. **Infraestrutura:** Docker First. Manter `.gitignore`, `.dockerignore` e `docker-compose.yml` atualizados.
9. **BIM:** Integração Half-way BIM na geração de arquivos .dxf (via accoreconsole.exe de modo headless para testes).

## Árvore de Pastas Padronizada (Fase 16.1)

```
calc_light/
├── MEMORY.md                          ← RAG do projeto (este arquivo)
├── backend/
│   ├── app/
│   │   ├── main.py                    ← FastAPI entry-point; APP_VERSION = "0.16.1"
│   │   ├── templates/
│   │   │   └── modelo.xlsm            ← Planilha modelo (keep_vba=True)
│   │   ├── domain/
│   │   │   ├── gis_parser.py          ← Motor de parsing KML/KMZ/GeoJSON/Excel (100% cov)
│   │   │   ├── excel_mapping.py       ← Dicionário estrito de células de entrada
│   │   │   ├── excel_exporter.py      ← Motor de exportação ZIP em lotes (memory-safe)
│   │   │   ├── calculators.py
│   │   │   ├── models.py              ← +is_ghost: bool = False em ProjectNodeBase
│   │   │   └── topology_service.py    ← Ghost: skip capacity, inclui tração; is_ghost no data
│   │   ├── api/
│   │   │   ├── routers/
│   │   │   │   ├── gis.py             ← POST parse-file, POST import-nodes, GET outgoing-conductors
│   │   │   │   ├── projects.py        ← +PATCH .../ghost; export filtra is_ghost
│   │   │   │   ├── calculations.py
│   │   │   │   ├── catalogs.py
│   │   │   │   ├── forces.py
│   │   │   │   └── topology.py
│   │   │   └── dependencies.py
│   │   ├── infrastructure/
│   │   │   └── database/
│   │   │       ├── database.py        ← +_apply_migrations(): ADD COLUMN is_ghost
│   │   │       └── repository.py      ← +set_node_ghost(), INSERT inclui is_ghost, bool cast
│   │   ├── schemas/
│   │   │   ├── gis.py
│   │   │   ├── projects.py            ← +is_ghost em ProjectNodeBase; +NodeGhostUpdate
│   │   │   ├── catalogs.py
│   │   │   └── topology.py
│   │   └── tests/
│   │       ├── test_api.py            ← fixture +is_ghost na CREATE TABLE
│   │       ├── test_ghost_node.py     ← 20 testes paranóicos ghost node
│   │       ├── test_gis_parser.py
│   │       ├── test_graph_inheritance.py ← fixture +is_ghost na CREATE TABLE
│   │       ├── test_excel_export.py
│   │       ├── test_calculators.py
│   │       ├── test_database.py       ← fixture +is_ghost na CREATE TABLE
│   │       └── test_topology.py
│   └── requirements.txt
├── frontend/
│   ├── package.json                   ← version: "0.16.1"
│   └── src/
│       ├── api.ts
│       ├── App.tsx
│       └── components/
│           ├── GisImportModal.tsx
│           ├── GhostNodeModal.tsx     ← Modal "Novo Poste" vs "Nó Fantasma"
│           ├── TopologyDiagram.tsx    ← +onConnectStart/End (drop-on-pane) + GhostNodeModal
│           ├── CustomNode.tsx         ← Ghost: border-dashed, opacity-50, sem badge de daN
│           ├── ExportButton.tsx
│           └── __tests__/
└── database/
```

## Domínio de Negócio (Cálculo de Tração)

A lógica principal de cálculo envolve Níveis (MT1, MT2, BT, Ramais) e Tramos (T1 a T4). As fórmulas extraídas da planilha são:
- **Tração dos Condutores (daN):** `(Peso_Total * Vão^2) / (8 * Flecha)`
- **Vento (daN):** `Força_Vento_X = Pressão_Vento * (Vão/2) * Diâmetro_Total * COS(Ângulo)`
- **Decomposição:** Tração decomposta em `Compx` e `Compy` de acordo com o ângulo do vão.
- **Resultante por Nível:** Soma vetorial das trações + Soma vetorial das forças de vento.
- **Resultante aplicada ao Poste:** Ajustada pelos momentos de alavanca (Altura Ancoragem / Altura Útil do Poste).

## Dicionário de Mapeamento de Células (excel_mapping.py)

Planilha alvo: `Ponto (1)` no `modelo.xlsm`.  Apenas inputs brutos; cálculos ficam com a planilha.

| Campo                     | Célula | Descrição                          |
|---------------------------|--------|------------------------------------|
| `orgao`                   | C1     | Órgão (ex: "OMET")                |
| `projeto`                 | H1     | Nome do projeto                    |
| `ponto`                   | K1     | Número sequencial do ponto/poste   |
| `data`                    | K3     | Data do estudo                     |
| `tipo_poste`              | C7     | Tipo do Poste                      |
| `modelo_poste`            | C8     | Modelo do Poste (ex: "11 m / 300 daN") |
| `mt1_t1_rede`             | C12    | MT 1º Nível – T1 – Tipo de rede   |
| `mt1_t1_cabo`             | C13    | MT 1º Nível – T1 – Tipo de cabo   |
| `mt1_t1_vao`              | C14    | MT 1º Nível – T1 – Vão (m)        |
| `mt1_t1_flecha`           | C15    | MT 1º Nível – T1 – Flecha (m)     |
| `mt1_t1_angulo`           | C16    | MT 1º Nível – T1 – Ângulo (°)     |
| `mt1_altura_poste`        | C17    | MT 1º Nível – Altura do poste (m) |
| `mt1_altura_ancoragem`    | C18    | MT 1º Nível – Altura ancoragem (m)|
| `mt1_t2_*` … `mt1_t4_*`  | F12-L16| MT 1º Nível – Tramos 2, 3 e 4     |
| `mt2_t1_*` … `mt2_t4_*`  | C38-L42| MT 2º Nível                        |
| `bt_t1_*` … `bt_t4_*`    | C64-L68| BT                                 |

## Nó Fantasma / Ghost Node (Fase 16.1)

### Conceito
Um "Nó Fantasma" representa um poste da rede existente da concessionária que serve de condição
de contorno (boundary condition) para o projeto. Ele **exerce tração mecânica** nos postes reais
do projeto através dos vãos que os conectam, mas **não é calculado, listado na BOM nem exportado**.

### Flag `is_ghost`
- **Tabela:** `project_nodes.is_ghost INTEGER DEFAULT 0`
- **Migração:** executada automaticamente em `database.py → _apply_migrations()` ao abrir conexão
- **Modelo:** `ProjectNode.is_ghost: bool = False` (domínio) e `ProjectNodeResponse.is_ghost: bool`

### Regras de Negócio (Não Negociáveis)
1. **Motor de Cálculo (topology_service.py):**
   - Vãos que conectam um poste real a um nó fantasma **contribuem com tração no poste real**
     (via `node_configs_map` para o `source_node_id` / `target_node_id`)
   - Para o próprio nó fantasma, o motor **NÃO computa** `effort_dan`, `utilization_percent`,
     `is_overloaded` nem `nominal_capacity` (todos ficam 0/False)
   - O nó fantasma **aparece no diagrama** (necessário para visualizar as arestas dos vãos)
   - `data["is_ghost"] = True` no payload do `TopologyNode`

2. **Exportação Excel / BOM:**
   - `nodes = [n for n in all_nodes if not n.is_ghost]` antes de qualquer iteração
   - Se após filtrar não sobrarem nós reais → HTTP 400 "Projeto vazio"
   - Nenhuma referência ao nó fantasma aparece no ZIP de exportação

3. **API:**
   - `PATCH /projects/{id}/nodes/{nid}/ghost` com `{ "is_ghost": true|false }` → toggle a flag
   - `POST /projects/{id}/nodes` com `"is_ghost": true` → cria diretamente como fantasma
   - `GET /topology/project/{id}` → inclui nós fantasmas no payload (para exibição) com `is_ghost=True`

### Visual no React Flow (CustomNode.tsx)
- `is_ghost=True`:
  - Opacidade **50%** (intencional — é "invisível" no senso que não pertence ao projeto)
  - Borda **tracejada** (`border-dashed border-slate-400/60`), paleta **cinza**
  - **SEM** badge de esforço (daN) — ghost não tem esforço calculado
  - Rótulo "Rede Existente" em lugar da badge
  - Tooltip explica o conceito ao engenheiro
- `is_ghost=False`: visual normal existente (Glassmorphism azul)

### Interação Drop-on-Pane (TopologyDiagram.tsx)
Quando o usuário arrasta a ponta de uma aresta e solta no **fundo do canvas** (sem nó destino):
1. `onConnectStart` captura `params.nodeId` (nó origem) em `connectSourceRef`
2. `onConnectEnd` verifica se o target foi o pane (não um nó/handle)
3. Abre `GhostNodeModal.tsx` com 2 opções:
   - **"Novo Poste"** → `POST /projects/{id}/nodes` + `POST /projects/{id}/edges` (is_ghost=false)
   - **"Nó Fantasma (Rede Existente)"** → idem com `is_ghost=true`
4. Novo nó é posicionado nas coordenadas do canvas onde o mouse foi solto

### Testes Paranóicos (test_ghost_node.py)
| Classe | Cenários |
|---|---|
| `TestGhostFlagPersistence` | DB salva/lê 0/1 corretamente; `get_project_nodes` converte para bool |
| `TestSetNodeGhost` | toggle true, toggle false, nó inexistente → None |
| `TestTopologyGhostBehavior` | ghost data["is_ghost"]=True; effort=0; P1 recebe tração de vão com ghost; real data["is_ghost"]=False; ghost aparece no diagrama |
| `TestExportGhostFilter` | ghost excluído da lista; lista com só ghosts → vazia |
| `TestGhostNodeAPI` | PATCH ghost=true/false; PATCH 404; export exclui ghost (ZIP tem 1 arquivo); export all-ghost → 400 |



- **Formatos suportados:** `.kml`, `.kmz`, `.geojson`, `.json`, `.xlsx`, `.xls`
- **Zero dependências C++:** usa apenas stdlib (`json`, `xml.etree`, `zipfile`, `io`) + `openpyxl`
- **`parse_file(filename, content)`:** dispatcher público por extensão
- **`parse_kml(content)`:** extrai Placemarks com ou sem namespace KML 2.2
- **`parse_kmz(content)`:** descomprime o ZIP e parseia o `.kml` interno
- **`parse_geojson(content)`:** extrai features `type=Point` com label de `properties.name/label`
- **`parse_excel(content)`:** lê colunas `lat/latitude`, `lng/lon/longitude`, `label/name/nome`
- **Erros graciosos:** arquivos malformados levantam `ValueError` → convertido para HTTP 400

## Lógica de Herança de Condutores (Fase 16)

Quando o usuário conecta uma nova aresta no React Flow (nó A → nó B):
1. O frontend chama `GET /projects/{id}/nodes/{A_id}/outgoing-conductors`
2. O backend busca o vão de saída mais recente de A (`source_node_id=A, ORDER BY id DESC LIMIT 1`)
3. Retorna `{ mt_conductor_id, mt_sag_m, bt_conductor_id, bt_sag_m }`
4. Se existir herança, o frontend usa esses valores no POST `/projects/{id}/edges`
5. Toast informa ao usuário se condutores foram herdados automaticamente ou não

**Regra de herança:** apenas o vão de saída mais recente (id DESC LIMIT 1) é herdado.
**Fallback:** se A não tiver vão de saída, a aresta é criada sem condutores (zeros/nulos).

## Importação Atômica GIS (Fase 16)

- **`POST /projects/{id}/parse-file`:** recebe upload de arquivo, retorna lista de `ParsedPoint`
- **`POST /projects/{id}/import-nodes`:** insere todos os pontos em uma única transação SQLite
  - Em caso de falha em qualquer inserção, o lote inteiro é revertido (rollback)
  - Nós importados têm `pole_id=0` (sem poste do catálogo) — o usuário configura depois
  - Posicionados em grade no canvas: `x = 500 + (i % 10) * 150`, `y = (i // 10) * 150`
- **`GisImportModal.tsx`:** Modal com lista de pontos parseados + checkboxes + confirmação

## Motor de Exportação em Lotes (excel_exporter.py)

- **`BATCH_SIZE = 30`**: máximo de arquivos por lote.
- **`build_poste_xlsm(data, template_path)`**: gera bytes de um único `.xlsm` com os dados injetados.
  - Workbook e BytesIO são fechados com `try/finally` (sem memory leaks).
- **`build_export_zip(postes_data, template_path)`**: gera ZIP mestre.
  - ≤ 30 postes → arquivos na raiz (`poste_01.xlsm`, …).
  - > 30 postes → subpastas `Lote_01/`, `Lote_02/`, … com até 30 arquivos cada.
  - Lista vazia → ZIP válido sem arquivos (sem erro).
  - BytesIO do ZIP fechado com `try/finally`.
- **Endpoint:** `GET /projects/{id}/export/excel` → `application/zip`.
  - HTTP 400 com `"Projeto vazio, adicione postes antes de exportar"` se não houver postes.
  - HTTP 404 se o projeto não existir.

## Equipe (Roles)

- **Tech Lead:** Orquestração geral do plano.
- **Dev Fullstack Sênior:** Codificação principal (Python/React).
- **DevOps/QA:** Garantia de testes, dockerização e cobertura de código.
- **UI/UX Designer:** Reproduzir a interface da planilha no modelo 2.5D.
- **Estagiário (Criatividade):** Soluções fora da caixa para problemas não mapeados.
