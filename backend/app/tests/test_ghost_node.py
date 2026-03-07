"""Testes paranóicos para a funcionalidade de Nó Fantasma (Ghost Node) — Fase 16.1.

Cenários cobertos:
1. Persistência: is_ghost salvo/recuperado corretamente (True e False)
2. set_node_ghost: toggle flag, nó não encontrado retorna None
3. get_project_nodes: converte is_ghost=0/1 corretamente para bool
4. Topologia: is_ghost=True no nó → data["is_ghost"]=True, effort_dan=0 (não calculado)
5. Topologia: tração do vão P1↔P2(ghost) é APLICADA no P1, mesmo P2 sendo ghost
6. Exportação: nós fantasmas são excluídos da lista de postes_data
7. API: PATCH /projects/{id}/nodes/{nid}/ghost retorna 200 e is_ghost correto
8. API: PATCH para nó inexistente retorna 404
9. API: export exclui ghost node e retorna ZIP com apenas postes reais
10. API: projeto com apenas ghost nodes retorna 400 no export (vazio)
"""

from __future__ import annotations

import io
import os
import sqlite3
import tempfile
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db, get_repository
from app.domain.models import (
    Conductor,
    NodeSpanConfig,
    Pole,
    ProjectNode,
)
from app.domain.topology_service import build_topology_diagram
from app.infrastructure.database.repository import ProjectRepository
from app.main import app

# ─── DB Fixture ──────────────────────────────────────────────────────────────


@pytest.fixture
def repo_path():
    """SQLite temporário com esquema mínimo + is_ghost."""
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
            pos_x REAL DEFAULT 0,
            pos_y REAL DEFAULT 0,
            effort_dan REAL DEFAULT 0,
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
    yield path
    try:
        os.remove(path)
    except PermissionError:
        pass


@pytest.fixture
def repo(repo_path):
    return ProjectRepository(db_path=repo_path)


def _insert_node(repo_path: str, project_id: int, label: str, is_ghost: bool = False) -> int:
    conn = sqlite3.connect(repo_path)
    cur = conn.execute(
        "INSERT INTO project_nodes (project_id, pole_id, label, is_ghost) VALUES (?, 0, ?, ?)",
        (project_id, label, 1 if is_ghost else 0),
    )
    conn.commit()
    node_id = cur.lastrowid
    conn.close()
    return node_id


def _insert_span(repo_path: str, src: int, tgt: int, mt_cond: int | None = None,
                 mt_sag: float = 0.5, span_len: float = 50.0) -> int:
    conn = sqlite3.connect(repo_path)
    cur = conn.execute(
        """INSERT INTO node_span_configs
           (source_node_id, target_node_id, mt_conductor_id, mt_sag_m, span_length_m, angle_deg)
           VALUES (?, ?, ?, ?, ?, 180.0)""",
        (src, tgt, mt_cond, mt_sag, span_len),
    )
    conn.commit()
    span_id = cur.lastrowid
    conn.close()
    return span_id


# ─── Repository unit tests ────────────────────────────────────────────────────


class TestGhostFlagPersistence:
    def test_add_node_real_is_ghost_false(self, repo, repo_path):
        node = ProjectNode(project_id=1, pole_id=0, label="P1", is_ghost=False)
        created = repo.add_node(node)
        assert created.id is not None
        # Verify directly in DB
        conn = sqlite3.connect(repo_path)
        row = conn.execute("SELECT is_ghost FROM project_nodes WHERE id=?", (created.id,)).fetchone()
        conn.close()
        assert row[0] == 0

    def test_add_node_ghost_is_ghost_true(self, repo, repo_path):
        node = ProjectNode(project_id=1, pole_id=0, label="Ghost", is_ghost=True)
        created = repo.add_node(node)
        assert created.is_ghost is True
        conn = sqlite3.connect(repo_path)
        row = conn.execute("SELECT is_ghost FROM project_nodes WHERE id=?", (created.id,)).fetchone()
        conn.close()
        assert row[0] == 1

    def test_get_project_nodes_maps_is_ghost_correctly(self, repo, repo_path):
        _insert_node(repo_path, 1, "Real", is_ghost=False)
        _insert_node(repo_path, 1, "Ghost", is_ghost=True)
        nodes = repo.get_project_nodes(1)
        labels = {n.label: n.is_ghost for n in nodes}
        assert labels["Real"] is False
        assert labels["Ghost"] is True


class TestSetNodeGhost:
    def test_set_ghost_true(self, repo, repo_path):
        node_id = _insert_node(repo_path, 1, "P1", is_ghost=False)
        updated = repo.set_node_ghost(node_id, True)
        assert updated is not None
        assert updated.is_ghost is True

    def test_set_ghost_false(self, repo, repo_path):
        node_id = _insert_node(repo_path, 1, "G1", is_ghost=True)
        updated = repo.set_node_ghost(node_id, False)
        assert updated is not None
        assert updated.is_ghost is False

    def test_set_ghost_nonexistent_node_returns_none(self, repo):
        result = repo.set_node_ghost(99999, True)
        assert result is None


# ─── Topology service unit tests ─────────────────────────────────────────────


def _make_conductor(cond_id: int = 1, weight_kg_m: float = 0.5) -> Conductor:
    return Conductor(
        id=cond_id,
        name="MT-Cable",
        diameter_m=0.015,
        weight_kg_m=weight_kg_m,
        cable_qty=3,
        network_type="MT",
    )


def _make_pole(pole_id: int = 1, resistance: float = 1000.0) -> Pole:
    return Pole(id=pole_id, type_name="DT-1000", height_m=11.0, resistance_dan=resistance)


class TestTopologyGhostBehavior:
    def test_ghost_node_has_is_ghost_true_in_data(self):
        nodes = [
            ProjectNode(id=1, project_id=1, pole_id=1, label="P1", is_ghost=False),
            ProjectNode(id=2, project_id=1, pole_id=0, label="Ghost", is_ghost=True),
        ]
        topo = build_topology_diagram(nodes, [], {}, {1: _make_pole()})
        ghost_data = next(n.data for n in topo.nodes if n.id == "2")
        assert ghost_data["is_ghost"] is True

    def test_ghost_node_effort_is_zero(self):
        """Ghost nodes nunca têm esforço calculado — retornam 0.0."""
        cond = _make_conductor()
        nodes = [
            ProjectNode(id=1, project_id=1, pole_id=1, label="P1"),
            ProjectNode(id=2, project_id=1, pole_id=0, label="Ghost", is_ghost=True),
        ]
        span = NodeSpanConfig(
            id=1, source_node_id=1, target_node_id=2,
            mt_conductor_id=1, mt_sag_m=0.5, span_length_m=50.0, angle_deg=180.0,
        )
        topo = build_topology_diagram(nodes, [span], {1: cond}, {1: _make_pole()})
        ghost_data = next(n.data for n in topo.nodes if n.id == "2")
        assert ghost_data["effort_dan"] == 0.0
        assert ghost_data["utilization_percent"] == 0.0
        assert ghost_data["is_overloaded"] is False
        assert ghost_data["nominal_capacity"] == 0.0

    def test_real_node_receives_traction_from_ghost_span(self):
        """A tração do cabo que liga P1 (real) ao P2 (ghost) deve ser aplicada em P1."""
        cond = _make_conductor(weight_kg_m=0.5)
        nodes = [
            ProjectNode(id=1, project_id=1, pole_id=1, label="P1"),
            ProjectNode(id=2, project_id=1, pole_id=0, label="Ghost", is_ghost=True),
        ]
        span = NodeSpanConfig(
            id=1, source_node_id=1, target_node_id=2,
            mt_conductor_id=1, mt_sag_m=0.5, span_length_m=50.0, angle_deg=180.0,
        )
        topo = build_topology_diagram(nodes, [span], {1: cond}, {1: _make_pole()})

        p1_data = next(n.data for n in topo.nodes if n.id == "1")
        # Tração manual: (0.5 kg/m * 3 cabos * 50^2) / (8 * 0.5) = 937.5 daN tração bruta
        # O effort_dan no poste é a resultante ajustada pelo braço de alavanca
        assert p1_data["effort_dan"] > 0.0, "P1 deve ter esforço > 0 por causa do vão com o ghost"

    def test_real_node_is_ghost_false_in_data(self):
        nodes = [ProjectNode(id=1, project_id=1, pole_id=1, label="P1")]
        topo = build_topology_diagram(nodes, [], {}, {1: _make_pole()})
        p1_data = topo.nodes[0].data
        assert p1_data["is_ghost"] is False

    def test_ghost_node_not_calculated_but_topology_includes_it(self):
        """Ghost nodes devem aparecer no diagrama (são necessários para a visualização dos vãos)."""
        nodes = [
            ProjectNode(id=10, project_id=1, pole_id=1, label="Real"),
            ProjectNode(id=11, project_id=1, pole_id=0, label="Ghost", is_ghost=True),
        ]
        topo = build_topology_diagram(nodes, [], {}, {1: _make_pole()})
        node_ids = {n.id for n in topo.nodes}
        assert "10" in node_ids
        assert "11" in node_ids


# ─── Export filter tests ──────────────────────────────────────────────────────


class TestExportGhostFilter:
    def test_real_nodes_included_in_export_data(self):
        """Simulação da lógica de export: apenas nós reais aparecem em postes_data."""
        all_nodes = [
            ProjectNode(id=1, project_id=1, pole_id=0, label="Real1"),
            ProjectNode(id=2, project_id=1, pole_id=0, label="Ghost", is_ghost=True),
            ProjectNode(id=3, project_id=1, pole_id=0, label="Real2"),
        ]
        nodes = [n for n in all_nodes if not n.is_ghost]
        assert len(nodes) == 2
        labels = {n.label for n in nodes}
        assert "Ghost" not in labels

    def test_only_ghost_nodes_yields_empty_list(self):
        all_nodes = [
            ProjectNode(id=1, project_id=1, pole_id=0, label="G1", is_ghost=True),
            ProjectNode(id=2, project_id=1, pole_id=0, label="G2", is_ghost=True),
        ]
        nodes = [n for n in all_nodes if not n.is_ghost]
        assert nodes == []


# ─── API integration tests ────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def temp_db_path_api():
    """DB temporário para testes de API."""
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
            pos_x REAL DEFAULT 0,
            pos_y REAL DEFAULT 0,
            effort_dan REAL DEFAULT 0,
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
        CREATE TABLE IF NOT EXISTS conductors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, diameter_m REAL, weight_kg_m REAL, cable_qty INTEGER, network_type TEXT,
            messenger_weight REAL, messenger_diameter REAL
        );
        CREATE TABLE IF NOT EXISTS poles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT, height_m REAL, resistance_dan REAL, weight_parameter_x REAL
        );
        INSERT INTO poles (type_name, height_m, resistance_dan, weight_parameter_x)
            VALUES ('DT-1000', 11, 1000, 0.0);
        INSERT INTO projects (name) VALUES ('Ghost Test Project');
    """)
    conn.commit()
    conn.close()
    yield path
    try:
        os.remove(path)
    except PermissionError:
        pass


@pytest.fixture(scope="module")
def api_client(temp_db_path_api):
    def override_get_db():
        conn = sqlite3.connect(temp_db_path_api)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def override_get_repo():
        return ProjectRepository(db_path=temp_db_path_api)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_repository] = override_get_repo

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


class TestGhostNodeAPI:
    def test_create_real_node_default_is_ghost_false(self, api_client):
        res = api_client.post("/projects/1/nodes", json={
            "project_id": 1, "pole_id": 1, "label": "P1-Real"
        })
        assert res.status_code == 200
        assert res.json()["is_ghost"] is False

    def test_create_ghost_node_via_api(self, api_client):
        res = api_client.post("/projects/1/nodes", json={
            "project_id": 1, "pole_id": 0, "label": "P2-Ghost", "is_ghost": True
        })
        assert res.status_code == 200
        assert res.json()["is_ghost"] is True

    def test_patch_ghost_flag_true(self, api_client, temp_db_path_api):
        conn = sqlite3.connect(temp_db_path_api)
        cur = conn.execute(
            "INSERT INTO project_nodes (project_id, pole_id, label, is_ghost) VALUES (1, 0, 'Toggle', 0)"
        )
        conn.commit()
        node_id = cur.lastrowid
        conn.close()

        res = api_client.patch(f"/projects/1/nodes/{node_id}/ghost", json={"is_ghost": True})
        assert res.status_code == 200
        assert res.json()["is_ghost"] is True

    def test_patch_ghost_flag_false(self, api_client, temp_db_path_api):
        conn = sqlite3.connect(temp_db_path_api)
        cur = conn.execute(
            "INSERT INTO project_nodes (project_id, pole_id, label, is_ghost) VALUES (1, 0, 'UnGhost', 1)"
        )
        conn.commit()
        node_id = cur.lastrowid
        conn.close()

        res = api_client.patch(f"/projects/1/nodes/{node_id}/ghost", json={"is_ghost": False})
        assert res.status_code == 200
        assert res.json()["is_ghost"] is False

    def test_patch_ghost_nonexistent_returns_404(self, api_client):
        res = api_client.patch("/projects/1/nodes/99999/ghost", json={"is_ghost": True})
        assert res.status_code == 404

    def test_export_excludes_ghost_nodes(self, api_client, temp_db_path_api):
        """Cenário paranóico: projeto com P1 (real) e P2 (ghost).
        O ZIP exportado deve conter apenas poste_01.xlsm (P1) — P2 é excluído.
        """
        conn = sqlite3.connect(temp_db_path_api)
        conn.execute("INSERT INTO projects (name) VALUES ('Export Ghost Test')")
        conn.commit()
        proj_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO project_nodes (project_id, pole_id, label, is_ghost) VALUES (?, 1, 'P1-Real', 0)",
            (proj_id,)
        )
        conn.execute(
            "INSERT INTO project_nodes (project_id, pole_id, label, is_ghost) VALUES (?, 0, 'P2-Ghost', 1)",
            (proj_id,)
        )
        conn.commit()
        conn.close()

        res = api_client.get(f"/projects/{proj_id}/export/excel")
        assert res.status_code == 200

        with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
            names = zf.namelist()
        # ZIP deve conter exatamente 1 arquivo (poste real), não 2
        assert len(names) == 1, f"ZIP deveria ter 1 arquivo mas tem {len(names)}: {names}"
        # O ghost não deve aparecer no ZIP
        assert not any("Ghost" in n for n in names), f"Ghost node vazou para o ZIP: {names}"

    def test_export_all_ghost_returns_400(self, api_client, temp_db_path_api):
        """Projeto com APENAS nós fantasmas deve retornar HTTP 400 na exportação."""
        conn = sqlite3.connect(temp_db_path_api)
        conn.execute("INSERT INTO projects (name) VALUES ('Only Ghost Project')")
        conn.commit()
        proj_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO project_nodes (project_id, pole_id, label, is_ghost) VALUES (?, 0, 'G1', 1)",
            (proj_id,)
        )
        conn.execute(
            "INSERT INTO project_nodes (project_id, pole_id, label, is_ghost) VALUES (?, 0, 'G2', 1)",
            (proj_id,)
        )
        conn.commit()
        conn.close()

        res = api_client.get(f"/projects/{proj_id}/export/excel")
        assert res.status_code == 400
        assert "vazio" in res.json()["detail"].lower()
