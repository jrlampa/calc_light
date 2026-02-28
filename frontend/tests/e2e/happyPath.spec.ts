import { test, expect, type Page } from '@playwright/test';

/**
 * URL base da API backend (interceptada pelo mock — sem necessidade do backend rodando).
 */
const API_URL = 'http://localhost:8001';

// ── Dados de mock ──────────────────────────────────────────────────────────

const POLES = [
  { id: 1, type_name: 'Concreto CP-600', height_m: 9, resistance_dan: 600 },
];

const CONDUCTORS = [
  {
    id: 1,
    name: 'Condutor MT 16mm²',
    diameter_m: 0.005,
    weight_kg_m: 0.12,
    cable_qty: 3,
    network_type: 'MT',
  },
];

const PROJECT = { id: 1, name: 'Projeto Teste E2E' };

const NODE_A = {
  id: 1,
  label: 'Poste A',
  pole_id: 1,
  project_id: 1,
  pos_x: 100,
  pos_y: 100,
  effort_dan: 0,
};

const NODE_B = {
  id: 2,
  label: 'Poste B',
  pole_id: 1,
  project_id: 1,
  pos_x: 300,
  pos_y: 100,
  effort_dan: 0,
};

const SPAN = {
  id: 1,
  source_node_id: 1,
  target_node_id: 2,
  span_length_m: 50,
  angle_deg: 0,
  mt_conductor_id: null,
  mt_sag_m: 0,
  bt_conductor_id: null,
  bt_sag_m: 0,
};

const TOPOLOGY = {
  nodes: [
    {
      id: '1',
      position: { x: 100, y: 100 },
      data: { label: 'Poste A', pole_type: 'Concreto CP-600', effort_dan: 0 },
    },
    {
      id: '2',
      position: { x: 300, y: 100 },
      data: { label: 'Poste B', pole_type: 'Concreto CP-600', effort_dan: 0 },
    },
  ],
  edges: [
    {
      id: '1',
      source: '1',
      target: '2',
      mt_label: null,
      mt_sag_m: null,
      bt_label: null,
      bt_sag_m: null,
      span_length_m: 50,
    },
  ],
};

const FORCE_VECTORS = [
  { level: 'MT1', component_x: 80, component_y: 40, magnitude_dan: 89.4, angle_deg: 26.6 },
  { level: 'RESULT', component_x: 80, component_y: 40, magnitude_dan: 89.4, angle_deg: 26.6 },
];

// ── Setup de mocks de API ──────────────────────────────────────────────────

/**
 * Registra os interceptores de rota do Playwright para simular o backend.
 * Utiliza closures para manter o estado dinâmico (lista de projetos e nós).
 */
async function setupApiMocks(page: Page) {
  const state = {
    projects: [] as typeof PROJECT[],
    nodes: [] as (typeof NODE_A | typeof NODE_B)[],
    nodePostCount: 0,
  };

  // Catálogos (estáticos)
  await page.route(`${API_URL}/catalogs/poles`, (route) =>
    route.fulfill({ json: POLES })
  );
  await page.route(`${API_URL}/catalogs/conductors`, (route) =>
    route.fulfill({ json: CONDUCTORS })
  );

  // Projetos (GET lista / POST criação)
  await page.route(`${API_URL}/projects`, async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: state.projects });
    } else if (route.request().method() === 'POST') {
      state.projects = [PROJECT];
      await route.fulfill({ status: 201, json: PROJECT });
    } else {
      await route.continue();
    }
  });

  // Nós do projeto (GET lista / POST criação)
  await page.route(`${API_URL}/projects/1/nodes`, async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: state.nodes });
    } else if (route.request().method() === 'POST') {
      state.nodePostCount += 1;
      const newNode = state.nodePostCount === 1 ? NODE_A : NODE_B;
      state.nodes = [...state.nodes, newNode];
      await route.fulfill({ status: 201, json: newNode });
    } else {
      await route.continue();
    }
  });

  // Vãos (POST criação)
  await page.route(`${API_URL}/projects/1/edges`, async (route) => {
    await route.fulfill({ status: 201, json: SPAN });
  });

  // Topologia calculada (GET)
  await page.route(`${API_URL}/topology/project/1`, async (route) => {
    await route.fulfill({ json: TOPOLOGY });
  });

  // Atualização de posição do nó (PATCH — silenciosa)
  await page.route(`${API_URL}/projects/1/nodes/*/position`, async (route) => {
    await route.fulfill({ json: { ok: true } });
  });

  // Diagrama de forças do nó 1 (GET)
  await page.route(`${API_URL}/forces-diagram/node/1`, async (route) => {
    await route.fulfill({ json: FORCE_VECTORS });
  });
}

// ── Suíte de testes ───────────────────────────────────────────────────────

test.describe('Caminho Principal — CACL LIGHT Fase 9', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test(
    'Cria projeto, adiciona Poste A e Poste B, cria vão, valida Unifilar e Diagrama de Forças',
    async ({ page }) => {
      // ── 1. Acessa a aplicação ──────────────────────────────────────────
      await page.goto('/');
      await expect(page.locator('text=CACL LIGHT')).toBeVisible();

      // ── 2. Cria um novo projeto via window.prompt ──────────────────────
      // Configura handler de diálogos antes de acionar qualquer ação
      page.on('dialog', async (dialog) => {
        if (dialog.type() === 'prompt') {
          await dialog.accept(PROJECT.name);
        } else {
          // Confirma ou descarta alertas de sucesso/erro
          await dialog.accept();
        }
      });

      await page.locator('button[title="Novo Projeto"]').click();

      // Aguarda o projeto aparecer na barra lateral
      await expect(page.locator(`text=${PROJECT.name}`)).toBeVisible();

      // Seleciona o projeto recém-criado
      await page.locator(`text=${PROJECT.name}`).click();

      // ── 3. Tab 1 — Adicionar Poste A ────────────────────────────────────
      await expect(page.locator('text=Adicionar Poste Físico')).toBeVisible();

      // Preenche o identificador do poste
      await page.locator('input[placeholder*="Poste Central"]').fill('Poste A');

      // Seleciona tipo de poste (primeiro item do catálogo mockado)
      await page.locator('select[name="pole_id"]').selectOption({ index: 1 });

      // Submete e aguarda o nó aparecer na lista de postes cadastrados
      await page.locator('button:has-text("Cadastrar Poste")').click();
      // Aguarda o span específico da lista (classe font-medium text-slate-700) com o label do poste
      await expect(
        page.locator('span.font-medium').filter({ hasText: /^Poste A$/ })
      ).toBeVisible();

      // ── 4. Tab 1 — Adicionar Poste B ────────────────────────────────────
      await page.locator('input[placeholder*="Poste Central"]').fill('Poste B');
      // O form faz reset() ao salvar — re-seleciona o tipo de poste
      await page.locator('select[name="pole_id"]').selectOption({ index: 1 });
      await page.locator('button:has-text("Cadastrar Poste")').click();
      await expect(
        page.locator('span.font-medium').filter({ hasText: /^Poste B$/ })
      ).toBeVisible();

      // ── 5. Tab 1 — Criar vão entre Poste A e Poste B ────────────────────
      await page.locator('select[name="source_node_id"]').selectOption({ label: 'Poste A' });
      await page.locator('select[name="target_node_id"]').selectOption({ label: 'Poste B' });
      await page.locator('input[name="span_length_m"]').fill('50');
      await page.locator('button:has-text("Estabelecer Conexão")').click();

      // ── 6. Navega para Tab 3 (Unifilar Topológico) ──────────────────────
      await page.locator('button:has-text("Unifilar Topológico")').click();

      // Aguarda o React Flow carregar e renderizar os 2 nós e 1 aresta
      await expect(page.locator('.react-flow__node')).toHaveCount(2, {
        timeout: 10_000,
      });
      await expect(page.locator('.react-flow__edge')).toHaveCount(1);

      // ── 7. Clica no primeiro nó e navega para Tab 2 (Diagrama de Forças) ─
      await page.locator('.react-flow__node').first().click();
      await page.locator('button:has-text("Diagrama de Forças")').click();

      // ── 8. Valida SVG e resultante do diagrama de forças ─────────────────
      // O seletor de postes deve listar Poste A (selecionado pelo clique no RF)
      await expect(page.locator('text=Selecione o Poste para Análise')).toBeVisible();

      // Seleciona o poste explicitamente para disparar o fetch de forças
      await page.locator('button:has-text("Poste A")').click();

      // Valida o SVG do diagrama vetorial (480×480 com viewBox específico)
      await expect(
        page.locator('svg[viewBox="0 0 480 480"]')
      ).toBeVisible({ timeout: 8_000 });

      // Valida a exibição da resultante em daN
      await expect(page.locator('text=Resultante:')).toBeVisible();
    }
  );
});
