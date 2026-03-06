"""Testes para o Modo Avançado de Arrasto de Equipamentos — Fase 19.

Cenários:
1. Com enable_equipment_drag=False, extra_drag_area_m2 não altera o resultado
2. Com enable_equipment_drag=True, extra_drag_area_m2 > 0 aumenta o esforço
3. build_topology_diagram com enable_equipment_drag=False ignora áreas
4. build_topology_diagram com enable_equipment_drag=True soma áreas
5. API GET /catalogs/equipment retorna catálogo
6. API PATCH /projects/{id}/settings atualiza flag
7. API GET /projects/{id}/nodes/{nid}/equipment retorna lista vazia
8. API PUT /projects/{id}/nodes/{nid}/equipment persiste equipamentos
9. Repositório: set_node_equipment_ids é idempotente (replace)
10. Repositório: get_node_equipment_total_area soma corretamente
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db, get_repository
from app.domain.calculators import calculate_level_resultant
from app.domain.models import (
    CalculationInput,
    Conductor,
    NodeSpanConfig,
    Pole,
    ProjectNode,
)
from app.domain.topology_service import build_topology_diagram
from app.infrastructure.database.repository import ProjectRepository
from app.main import app

# ─── Fixtures ────────────────────────────────────────────────────────────────


def _cond(cid: int = 1) -> Conductor:
    return Conductor(
        id=cid,
        name="MT-Test",
        diameter_m=0.015,
        weight_kg_m=0.5,
        cable_qty=3,
        network_type="MT",
        messenger_diameter=0.0,
        messenger_weight=0.0,
    )


def _inp(span: float = 50.0, sag: float = 0.5, angle: float = 0.0) -> CalculationInput:
    return CalculationInput(
        span_m=span,
        sag_m=sag,
        angle_deg=angle,
        pole_height_m=11.0,
        anchorage_height_m=8.5,
        conductor_id=1,
        level="MT1",
        level_order=1,
    )


def _pole(pid: int = 1, resistance: float = 600.0) -> Pole:
    return Pole(id=pid, type_name="DT-600", height_m=11.0, resistance_dan=resistance)


def _node(nid: int = 1, pole_id: int = 1) -> ProjectNode:
    return ProjectNode(
        id=nid,
        project_id=1,
        pole_id=pole_id,
        label=f"P{nid}",
        pos_x=float(nid * 100),
        pos_y=0.0,
    )


# ─── Banco em memória para testes de repositório ─────────────────────────────


def _make_db() -> tuple[str, sqlite3.Connection]:
    """Cria um banco SQLite temporário com as tabelas necessárias para os testes."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            enable_equipment_drag INTEGER DEFAULT 0
        );
        CREATE TABLE poles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT,
            height_m REAL,
            resistance_dan REAL,
            weight_parameter_x REAL DEFAULT 0.0
        );
        CREATE TABLE project_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            pole_id INTEGER,
            label TEXT,
            pos_x REAL DEFAULT 0.0,
            pos_y REAL DEFAULT 0.0,
            effort_dan REAL DEFAULT 0.0,
            is_ghost INTEGER DEFAULT 0
        );
        CREATE TABLE node_span_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_node_id INTEGER,
            target_node_id INTEGER,
            mt_conductor_id INTEGER,
            mt_sag_m REAL DEFAULT 0.0,
            bt_conductor_id INTEGER,
            bt_sag_m REAL DEFAULT 0.0,
            span_length_m REAL DEFAULT 0.0,
            angle_deg REAL DEFAULT 0.0
        );
        CREATE TABLE catalog_equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            area_arrasto_m2 REAL NOT NULL
        );
        CREATE TABLE node_equipment (
            node_id INTEGER NOT NULL,
            equipment_id INTEGER NOT NULL,
            PRIMARY KEY (node_id, equipment_id)
        );
        INSERT INTO poles (type_name, height_m, resistance_dan) VALUES ('DT-600', 11.0, 600.0);
        INSERT INTO projects (name) VALUES ('Proj Teste');
        INSERT INTO project_nodes (project_id, pole_id, label) VALUES (1, 1, 'P1');
        INSERT INTO project_nodes (project_id, pole_id, label) VALUES (1, 1, 'P2');
        INSERT INTO catalog_equipment (name, area_arrasto_m2) VALUES ('Trafo 45 kVA', 0.85);
        INSERT INTO catalog_equipment (name, area_arrasto_m2) VALUES ('Cruzeta 2m', 0.30);
        """
    )
    conn.commit()
    return path, conn


# ─── Testes de Domínio (Calculators) ─────────────────────────────────────────


def test_extra_drag_disabled_no_change():
    """Com extra_drag_area_m2=0 (default), o resultado deve ser idêntico ao original."""
    inp = _inp()
    c = _cond()
    result_no_drag = calculate_level_resultant([inp], [c])
    result_zero_drag = calculate_level_resultant([inp], [c], extra_drag_area_m2=0.0)
    assert result_no_drag.wind_force_x == result_zero_drag.wind_force_x
    assert result_no_drag.traction_on_pole_dan == result_zero_drag.traction_on_pole_dan


def test_extra_drag_increases_wind_force():
    """Com extra_drag_area_m2 > 0, a força de vento X deve ser maior."""
    inp = _inp(angle=0.0)
    c = _cond()
    result_base = calculate_level_resultant([inp], [c], extra_drag_area_m2=0.0)
    result_drag = calculate_level_resultant([inp], [c], extra_drag_area_m2=0.85)
    assert result_drag.wind_force_x > result_base.wind_force_x


def test_extra_drag_zero_span_safe():
    """Com span_m=0 (divisão por zero), não deve lançar exceção."""
    inp = _inp(span=0.0, sag=0.5)
    c = _cond()
    # Não deve lançar exceção
    result = calculate_level_resultant([inp], [c], extra_drag_area_m2=0.85)
    assert result.wind_force_x == 0.0  # Sem span não há vento


# ─── Testes de build_topology_diagram ────────────────────────────────────────


def _make_topo_data():
    nodes = [_node(1), _node(2)]
    c = _cond()
    spans = [
        NodeSpanConfig(
            id=1,
            source_node_id=1,
            target_node_id=2,
            mt_conductor_id=1,
            mt_sag_m=0.5,
            span_length_m=50.0,
            angle_deg=0.0,
        )
    ]
    conductors = {1: c}
    poles = {1: _pole()}
    return nodes, spans, conductors, poles


def test_topology_drag_disabled_ignores_areas():
    """Com enable_equipment_drag=False, as áreas de equipamento são ignoradas."""
    nodes, spans, conductors, poles = _make_topo_data()
    topo_no_drag = build_topology_diagram(nodes, spans, conductors, poles, enable_equipment_drag=False)
    topo_with_areas = build_topology_diagram(
        nodes, spans, conductors, poles,
        enable_equipment_drag=False,
        node_equipment_areas={1: 2.0, 2: 2.0},
    )
    n1_no = next(n for n in topo_no_drag.nodes if n.id == "1")
    n1_wi = next(n for n in topo_with_areas.nodes if n.id == "1")
    assert n1_no.data["effort_dan"] == n1_wi.data["effort_dan"]


def test_topology_drag_enabled_increases_effort():
    """Com enable_equipment_drag=True e áreas > 0, o esforço deve ser maior."""
    nodes, spans, conductors, poles = _make_topo_data()
    topo_base = build_topology_diagram(nodes, spans, conductors, poles, enable_equipment_drag=False)
    topo_drag = build_topology_diagram(
        nodes, spans, conductors, poles,
        enable_equipment_drag=True,
        node_equipment_areas={1: 0.85, 2: 0.85},
    )
    n1_base = next(n for n in topo_base.nodes if n.id == "1")
    n1_drag = next(n for n in topo_drag.nodes if n.id == "1")
    assert n1_drag.data["effort_dan"] > n1_base.data["effort_dan"]


def test_topology_drag_enabled_no_areas_no_change():
    """Com enable_equipment_drag=True mas sem áreas, o esforço não muda."""
    nodes, spans, conductors, poles = _make_topo_data()
    topo_base = build_topology_diagram(nodes, spans, conductors, poles, enable_equipment_drag=False)
    topo_drag = build_topology_diagram(
        nodes, spans, conductors, poles,
        enable_equipment_drag=True,
        node_equipment_areas={},  # sem equipamentos
    )
    n1_base = next(n for n in topo_base.nodes if n.id == "1")
    n1_drag = next(n for n in topo_drag.nodes if n.id == "1")
    assert n1_base.data["effort_dan"] == n1_drag.data["effort_dan"]


# ─── Testes de Repositório ────────────────────────────────────────────────────


def test_repo_set_get_node_equipment():
    path, _ = _make_db()
    repo = ProjectRepository(db_path=path)
    ids = repo.set_node_equipment_ids(node_id=1, equipment_ids=[1, 2])
    assert set(ids) == {1, 2}
    retrieved = repo.get_node_equipment_ids(1)
    assert set(retrieved) == {1, 2}


def test_repo_set_node_equipment_replace():
    """set_node_equipment_ids deve fazer REPLACE (substituição completa)."""
    path, _ = _make_db()
    repo = ProjectRepository(db_path=path)
    repo.set_node_equipment_ids(node_id=1, equipment_ids=[1, 2])
    # Substituir — somente o ID 1 deve restar
    ids = repo.set_node_equipment_ids(node_id=1, equipment_ids=[1])
    assert ids == [1]


def test_repo_get_node_equipment_total_area():
    path, _ = _make_db()
    repo = ProjectRepository(db_path=path)
    repo.set_node_equipment_ids(node_id=1, equipment_ids=[1, 2])  # 0.85 + 0.30 = 1.15
    total = repo.get_node_equipment_total_area(node_id=1)
    assert abs(total - 1.15) < 1e-9


def test_repo_get_node_equipment_total_area_empty():
    path, _ = _make_db()
    repo = ProjectRepository(db_path=path)
    total = repo.get_node_equipment_total_area(node_id=1)
    assert total == 0.0


def test_repo_update_project_settings():
    path, _ = _make_db()
    repo = ProjectRepository(db_path=path)
    updated = repo.update_project_settings(project_id=1, enable_equipment_drag=True)
    assert updated is not None
    assert updated.enable_equipment_drag is True
    # Reverter
    updated2 = repo.update_project_settings(project_id=1, enable_equipment_drag=False)
    assert updated2.enable_equipment_drag is False


def test_repo_update_project_settings_not_found():
    path, _ = _make_db()
    repo = ProjectRepository(db_path=path)
    result = repo.update_project_settings(project_id=9999, enable_equipment_drag=True)
    assert result is None


# ─── Testes de API ────────────────────────────────────────────────────────────


@pytest.fixture()
def client_and_db():
    """Cliente de teste com banco temporário."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            enable_equipment_drag INTEGER DEFAULT 0
        );
        CREATE TABLE poles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT,
            height_m REAL,
            resistance_dan REAL,
            weight_parameter_x REAL DEFAULT 0.0
        );
        CREATE TABLE conductors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            diameter_m REAL DEFAULT 0.0,
            weight_kg_m REAL DEFAULT 0.0,
            cable_qty INTEGER DEFAULT 1,
            network_type TEXT DEFAULT 'Conv',
            messenger_diameter REAL DEFAULT 0.0,
            messenger_weight REAL DEFAULT 0.0
        );
        CREATE TABLE project_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            pole_id INTEGER,
            label TEXT,
            pos_x REAL DEFAULT 0.0,
            pos_y REAL DEFAULT 0.0,
            effort_dan REAL DEFAULT 0.0,
            is_ghost INTEGER DEFAULT 0
        );
        CREATE TABLE node_span_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_node_id INTEGER,
            target_node_id INTEGER,
            mt_conductor_id INTEGER,
            mt_sag_m REAL DEFAULT 0.0,
            bt_conductor_id INTEGER,
            bt_sag_m REAL DEFAULT 0.0,
            span_length_m REAL DEFAULT 0.0,
            angle_deg REAL DEFAULT 0.0
        );
        CREATE TABLE catalog_equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            area_arrasto_m2 REAL NOT NULL
        );
        CREATE TABLE node_equipment (
            node_id INTEGER NOT NULL,
            equipment_id INTEGER NOT NULL,
            PRIMARY KEY (node_id, equipment_id)
        );
        INSERT INTO projects (name) VALUES ('Proj API');
        INSERT INTO poles (type_name, height_m, resistance_dan) VALUES ('DT-600', 11.0, 600.0);
        INSERT INTO project_nodes (project_id, pole_id, label) VALUES (1, 1, 'P1');
        INSERT INTO catalog_equipment (name, area_arrasto_m2) VALUES ('Trafo 45 kVA', 0.85);
        INSERT INTO catalog_equipment (name, area_arrasto_m2) VALUES ('Cruzeta 2m', 0.30);
        """
    )
    conn.commit()

    repo = ProjectRepository(db_path=path)

    def _override_db():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    def _override_repo():
        return repo

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_repository] = _override_repo
    client = TestClient(app)
    yield client, path
    app.dependency_overrides.clear()
    try:
        os.unlink(path)
    except OSError:
        pass


def test_api_get_equipment_catalog(client_and_db):
    client, _ = client_and_db
    resp = client.get("/catalogs/equipment")
    assert resp.status_code == 200
    data = resp.json()
    names = [e["name"] for e in data]
    assert "Trafo 45 kVA" in names
    assert "Cruzeta 2m" in names
    for e in data:
        assert "area_arrasto_m2" in e
        assert e["area_arrasto_m2"] > 0


def test_api_patch_project_settings(client_and_db):
    client, _ = client_and_db
    resp = client.patch("/projects/1/settings", json={"enable_equipment_drag": True})
    assert resp.status_code == 200
    assert resp.json()["enable_equipment_drag"] is True


def test_api_patch_project_settings_not_found(client_and_db):
    client, _ = client_and_db
    resp = client.patch("/projects/9999/settings", json={"enable_equipment_drag": True})
    assert resp.status_code == 404


def test_api_get_node_equipment_empty(client_and_db):
    client, _ = client_and_db
    resp = client.get("/projects/1/nodes/1/equipment")
    assert resp.status_code == 200
    assert resp.json() == []


def test_api_put_node_equipment(client_and_db):
    client, _ = client_and_db
    resp = client.put("/projects/1/nodes/1/equipment", json={"equipment_ids": [1, 2]})
    assert resp.status_code == 200
    assert set(resp.json()) == {1, 2}


def test_api_put_node_equipment_replace(client_and_db):
    """PUT /equipment deve substituir (não acumular)."""
    client, _ = client_and_db
    client.put("/projects/1/nodes/1/equipment", json={"equipment_ids": [1, 2]})
    resp = client.put("/projects/1/nodes/1/equipment", json={"equipment_ids": [1]})
    assert resp.status_code == 200
    assert resp.json() == [1]
