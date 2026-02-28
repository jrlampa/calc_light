# CACL_LIGHT - Project Memory (RAG)

## Contexto do Projeto

O projeto **CACL_LIGHT** é um sistema web (React + FastAPI + SQLite3) projetado para substituir planilhas complexas de engenharia elétrica (como "CÁLCULO DE TRAÇÃO OII-25-2249.xlsm" e "POSTE69.xlsm"). O objetivo é realizar o cálculo de esforços mecânicos em postes de distribuição de energia, garantindo precisão idêntica à planilha original.

**Versão atual:** `0.15.1` (Fase 15.1 — Quality Gate)

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

## Árvore de Pastas Padronizada (Fase 15.1)

```
calc_light/
├── MEMORY.md                          ← RAG do projeto (este arquivo)
├── backend/
│   ├── app/
│   │   ├── main.py                    ← FastAPI entry-point; APP_VERSION = "0.15.1"
│   │   ├── templates/
│   │   │   └── modelo.xlsm            ← Planilha modelo (keep_vba=True)
│   │   ├── domain/
│   │   │   ├── excel_mapping.py       ← Dicionário estrito de células de entrada
│   │   │   ├── excel_exporter.py      ← Motor de exportação ZIP em lotes (memory-safe)
│   │   │   ├── calculators.py
│   │   │   ├── models.py
│   │   │   └── topology_service.py
│   │   ├── api/
│   │   │   ├── routers/
│   │   │   │   ├── projects.py        ← Inclui GET /{id}/export/excel; HTTP 400 para projeto vazio
│   │   │   │   ├── calculations.py
│   │   │   │   ├── catalogs.py
│   │   │   │   ├── forces.py
│   │   │   │   └── topology.py
│   │   │   └── dependencies.py
│   │   ├── infrastructure/
│   │   │   └── database/
│   │   │       ├── database.py
│   │   │       └── repository.py
│   │   ├── schemas/
│   │   │   ├── projects.py
│   │   │   ├── catalogs.py
│   │   │   └── topology.py
│   │   └── tests/
│   │       ├── test_api.py            ← Inclui testes HTTP 400/404 para export
│   │       ├── test_excel_export.py   ← 24 testes paranóicos (35 postes, lotes, células, lista vazia)
│   │       ├── test_calculators.py
│   │       ├── test_database.py
│   │       └── test_topology.py
│   └── requirements.txt
├── frontend/
│   ├── package.json                   ← version: "0.15.1"
│   └── src/
│       ├── api.ts                     ← downloadProjectExcel()
│       ├── App.tsx                    ← Usa ExportButton; trata HTTP 400 com toast específico
│       └── components/
│           ├── ExportButton.tsx       ← Botão isolado (SRP); testável com Vitest
│           └── __tests__/
│               ├── ExportButton.test.tsx  ← 7 testes Vitest (≥80% cobertura)
│               ├── CustomNode.test.tsx
│               └── CustomEdge.test.tsx
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
