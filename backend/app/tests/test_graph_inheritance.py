"""Testes de unidade para a Lógica de Herança de Condutores e importação atômica.

Cobertura exigida: 100% dos novos métodos do ProjectRepository:
- import_nodes_atomic: happy path, lista vazia, rollback em caso de falha
- get_outgoing_span_config: existe, não existe, retorna o mais recente (DESC id)

Estes testes usam SQLite em memória (tempfile) para garantir isolamento total.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from app.domain.models import NodeSpanConfig, ProjectNode
from app.infrastructure.database.repository import ProjectRepository

# ─── Fixture: banco de dados mínimo em arquivo temporário ────────────────────


@pytest.fixture
def repo():
    """Cria um ProjectRepository apontando para um SQLite temporário com esquema mínimo."""
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)

    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS project_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            pole_id INTEGER,
            label TEXT,
            pos_x REAL,
            pos_y REAL,
            effort_dan REAL,
            is_ghost INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS node_span_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_node_id INTEGER NOT NULL,
            target_node_id INTEGER NOT NULL,
            mt_conductor_id INTEGER,
            mt_sag_m REAL DEFAULT 0.0,
            bt_conductor_id INTEGER,
            bt_sag_m REAL DEFAULT 0.0,
            span_length_m REAL DEFAULT 0.0,
            angle_deg REAL DEFAULT 0.0
        );
    """)
    conn.close()

    yield ProjectRepository(db_path=path)

    try:
        os.remove(path)
    except PermissionError:
        pass


def _make_node(project_id: int = 1, label: str = "P") -> ProjectNode:
    return ProjectNode(project_id=project_id, pole_id=0, label=label, pos_x=0.0, pos_y=0.0)


# ─── import_nodes_atomic ─────────────────────────────────────────────────────


class TestImportNodesAtomic:
    def test_empty_list_returns_empty(self, repo):
        result = repo.import_nodes_atomic([])
        assert result == []

    def test_single_node_gets_id_assigned(self, repo):
        nodes = [_make_node(label="P1")]
        result = repo.import_nodes_atomic(nodes)
        assert len(result) == 1
        assert result[0].id is not None
        assert result[0].id > 0
        assert result[0].label == "P1"

    def test_multiple_nodes_all_inserted(self, repo):
        nodes = [_make_node(label=f"P{i}") for i in range(5)]
        result = repo.import_nodes_atomic(nodes)
        assert len(result) == 5
        ids = [n.id for n in result]
        assert len(set(ids)) == 5, "Todos os IDs devem ser únicos"

    def test_nodes_persisted_in_db(self, repo):
        nodes = [_make_node(label="Stored")]
        repo.import_nodes_atomic(nodes)

        conn = sqlite3.connect(repo.db_path)
        row = conn.execute("SELECT label FROM project_nodes WHERE label='Stored'").fetchone()
        conn.close()
        assert row is not None

    def test_rollback_on_failure_leaves_db_clean(self, repo):
        """Se uma inserção falhar, NENHUM nó do lote deve persistir."""
        # Add UNIQUE constraint to force a failure on the second identical label
        conn = sqlite3.connect(repo.db_path)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_rollback_label ON project_nodes(label)")
        conn.commit()
        conn.close()

        # Two nodes with the same label → second INSERT violates UNIQUE → rollback
        nodes = [_make_node(label="DUPE"), _make_node(label="DUPE")]
        with pytest.raises(Exception, match="."):
            repo.import_nodes_atomic(nodes)

        conn = sqlite3.connect(repo.db_path)
        count = conn.execute("SELECT COUNT(*) FROM project_nodes WHERE label='DUPE'").fetchone()[0]

        # Cleanup the index so other tests are not affected
        conn.execute("DROP INDEX IF EXISTS ux_rollback_label")
        conn.commit()
        conn.close()

        assert count == 0, f"Rollback falhou: {count} nó(s) encontrado(s) no banco"


# ─── get_outgoing_span_config ────────────────────────────────────────────────


class TestGetOutgoingSpanConfig:
    def _insert_span(
        self,
        repo,
        source: int,
        target: int,
        mt_id: int | None = None,
        mt_sag: float = 0.0,
        bt_id: int | None = None,
        bt_sag: float = 0.0,
    ) -> int:
        conn = sqlite3.connect(repo.db_path)
        cur = conn.execute(
            """
            INSERT INTO node_span_configs
            (source_node_id, target_node_id, mt_conductor_id, mt_sag_m,
             bt_conductor_id, bt_sag_m, span_length_m, angle_deg)
            VALUES (?, ?, ?, ?, ?, ?, 50.0, 0.0)
            """,
            (source, target, mt_id, mt_sag, bt_id, bt_sag),
        )
        conn.commit()
        span_id = cur.lastrowid
        conn.close()
        return span_id

    def test_returns_none_when_no_spans(self, repo):
        result = repo.get_outgoing_span_config(node_id=999)
        assert result is None

    def test_returns_span_when_exists(self, repo):
        self._insert_span(repo, source=1, target=2, mt_id=5, mt_sag=1.2)
        result = repo.get_outgoing_span_config(node_id=1)
        assert result is not None
        assert isinstance(result, NodeSpanConfig)
        assert result.source_node_id == 1
        assert result.mt_conductor_id == 5
        assert result.mt_sag_m == pytest.approx(1.2)

    def test_returns_most_recent_span_on_multiple(self, repo):
        """Com múltiplos vãos de saída, retorna o de maior id (mais recente)."""
        self._insert_span(repo, source=10, target=11, mt_id=1)
        self._insert_span(repo, source=10, target=12, mt_id=2)
        latest_id = self._insert_span(repo, source=10, target=13, mt_id=3, mt_sag=0.9)

        result = repo.get_outgoing_span_config(node_id=10)
        assert result is not None
        assert result.id == latest_id
        assert result.mt_conductor_id == 3
        assert result.mt_sag_m == pytest.approx(0.9)

    def test_does_not_return_incoming_spans(self, repo):
        """Vãos onde o nó é target (não source) não devem ser retornados."""
        self._insert_span(repo, source=20, target=30, mt_id=7)
        result = repo.get_outgoing_span_config(node_id=30)  # target node
        assert result is None

    def test_bt_conductor_inherited_correctly(self, repo):
        """Condutores BT também devem ser retornados para herança."""
        self._insert_span(repo, source=40, target=41, bt_id=99, bt_sag=0.5)
        result = repo.get_outgoing_span_config(node_id=40)
        assert result is not None
        assert result.bt_conductor_id == 99
        assert result.bt_sag_m == pytest.approx(0.5)
        assert result.mt_conductor_id is None


# ─── Teste de Integração Pura: Simulação da Herança de Condutores ─────────────


class TestConductorInheritanceIntegration:
    """
    Simula o fluxo completo da Herança de Condutores no Python (sem HTTP):
    1. Nó A existe com cabo MT configurado no vão A→X.
    2. Usuário conecta A→B (novo nó sem cabos).
    3. O sistema consulta o vão de saída de A e retorna o mt_conductor_id.
    4. A nova aresta A→B herda o cabo X de A.
    """

    def test_inheritance_full_flow(self, repo):
        # Setup: inserir vão A→X com MT conductor_id=10
        conn = sqlite3.connect(repo.db_path)
        conn.execute("""
            INSERT INTO node_span_configs
            (source_node_id, target_node_id, mt_conductor_id, mt_sag_m,
             bt_conductor_id, bt_sag_m, span_length_m, angle_deg)
            VALUES (1, 99, 10, 0.8, NULL, 0.0, 50.0, 180.0)
        """)
        conn.commit()
        conn.close()

        # Consultar herança para o nó A (id=1)
        inherited = repo.get_outgoing_span_config(node_id=1)

        # Assertions: a aresta A→B deve herdar mt_conductor_id=10 e mt_sag_m=0.8
        assert inherited is not None
        assert inherited.mt_conductor_id == 10, "Cabo MT herdado deve ser 10"
        assert inherited.mt_sag_m == pytest.approx(0.8), "Flecha MT herdada deve ser 0.8"
        assert inherited.bt_conductor_id is None, "Sem BT a herdar"

    def test_no_inheritance_when_source_has_no_spans(self, repo):
        """Nó sem vão de saída → herança retorna None → aresta criada sem cabos."""
        result = repo.get_outgoing_span_config(node_id=500)
        assert result is None, "Nó sem vão de saída não deve herdar condutores"
