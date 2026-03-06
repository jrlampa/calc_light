"""Testes paranóicos para o Motor de Otimização (Solver Global) — Fase 17.

Cenários (100% de cobertura em solver.py):
1. Poste normal (esforço <= 2000 daN) → sem sugestão
2. Poste sobrecarregado resolvido com flecha padrão (0.3–0.9 m) → is_extreme=False
3. Poste sobrecarregado resolvido apenas com flecha extrema (1.0–1.3 m) → is_extreme=True
4. Tração absurda (ex: esforço > 2000 daN mesmo com sag=1.3 m) → requires_span_break=True

Adicionalmente:
5. Nó fantasma nunca entra na análise
6. Nó sem vãos → esforço=0, sem sugestão
7. API GET /projects/{id}/solve retorna report correto
8. API POST /projects/{id}/solve/apply atualiza banco de dados
9. API para projeto inexistente → 404
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db, get_repository
from app.domain.models import Conductor, NodeSpanConfig, Pole, ProjectNode
from app.domain.solver import (
    MAX_STRUCTURAL_DAN,
    SAG_EXTREME,
    SAG_STANDARD,
    _compute_effort,
    run_solver,
)
from app.infrastructure.database.repository import ProjectRepository
from app.main import app

# ─── Fixtures de Dados ────────────────────────────────────────────────────────


def _cond(cid: int = 1, weight: float = 0.5, qty: int = 3, diam: float = 0.015) -> Conductor:
    return Conductor(
        id=cid,
        name="Mock MT",
        diameter_m=diam,
        weight_kg_m=weight,
        cable_qty=qty,
        network_type="MT",
    )


def _pole(pid: int = 1, resistance: float = 1000.0) -> Pole:
    return Pole(id=pid, type_name="DT-1000", height_m=11.0, resistance_dan=resistance)


def _node(nid: int = 1, pole_id: int = 1, is_ghost: bool = False) -> ProjectNode:
    return ProjectNode(
        id=nid, project_id=1, pole_id=pole_id, label=f"P{nid}", is_ghost=is_ghost
    )


def _span(span_id: int = 1, src: int = 1, tgt: int = 2,
          mt_cond: int = 1, mt_sag: float = 0.5, span_m: float = 50.0) -> NodeSpanConfig:
    return NodeSpanConfig(
        id=span_id,
        source_node_id=src,
        target_node_id=tgt,
        mt_conductor_id=mt_cond,
        mt_sag_m=mt_sag,
        span_length_m=span_m,
        angle_deg=0.0,
    )


# ─── Testes Unitários — run_solver ────────────────────────────────────────────


class TestSolverScenarios:
    """Cobre os 4 cenários paranóicos obrigatórios."""

    def test_cenario1_poste_normal_sem_sugestao(self):
        """Poste com esforço baixo não gera sugestão."""
        # Vão de 50 m, flecha 0.5 m, peso=0.5 kg/m × 3 cabos = 1.5 kg/m
        # Tração bruta ≈ (1.5 × 50²) / (8 × 0.5) = 937.5 daN — ANTES do braço de alavanca
        # traction_on_pole_dan é menor ainda — << 2000 daN
        node = _node(1, pole_id=1)
        span = _span(1, src=1, tgt=2)
        conds = {1: _cond()}
        poles = {1: _pole(resistance=2000.0)}

        report = run_solver(1, [node, _node(2, pole_id=0, is_ghost=True)], [span], conds, poles)

        assert report.overloaded_count == 0
        assert report.solvable_count == 0
        assert report.requires_span_break_count == 0
        assert report.suggestions == []

    def test_cenario2_resolvido_flecha_padrao(self):
        """Poste sobrecarregado resolvido dentro do range padrão (0.3–0.9 m).

        Para forçar sobrecarga: usamos span muito grande (300 m) com flecha pequena (0.1 m)
        mas nominal_capacity baixo (200 daN) e esforço acima de 2000 daN absoluto.
        Criamos o cenário com vão 200 m e flecha 0.1 m para ter tração enorme.
        """
        # weight_total = 0.5 × 3 = 1.5 kg/m; tração = (1.5 × 200²) / (8 × 0.1) = 75000 daN
        # Com braço de alavanca: × (8.5 / (11×0.9-0.7)) = × (8.5/9.2) ≈ 0.924
        # traction_on_pole ≈ 75000 × 0.924 ≈ 69300 daN >> 2000
        # Com sag=0.9 m: tração = (1.5 × 200²) / (8 × 0.9) = 8333 daN — ainda >> 2000
        # Preciso de vão menor: vão=50m, flecha=0.1 m → tração=(1.5×2500)/(8×0.1)=4687.5 daN × 0.924≈4331
        # Com sag=0.5m: (1.5×2500)/(8×0.5)=937.5×0.924≈866 daN — OK!
        # Portanto: flecha inicial=0.1m → overloaded; flecha=0.5m → solved (padrão)
        node = _node(1, pole_id=1)
        span = _span(1, src=1, tgt=2, mt_sag=0.1, span_m=50.0)
        conds = {1: _cond()}
        poles = {1: _pole(resistance=2000.0)}

        report = run_solver(1, [node, _node(2, pole_id=0, is_ghost=True)], [span], conds, poles)

        assert report.overloaded_count == 1
        assert report.solvable_count == 1
        assert report.requires_span_break_count == 0
        assert len(report.suggestions) == 1

        sug = report.suggestions[0]
        assert sug.node_id == 1
        assert sug.current_effort_dan > MAX_STRUCTURAL_DAN
        assert sug.target_effort_dan is not None
        assert sug.target_effort_dan <= MAX_STRUCTURAL_DAN
        assert sug.is_extreme is False
        assert sug.requires_span_break is False
        # Flecha sugerida deve estar no range padrão
        assert any(
            abs(ss.new_mt_sag_m - s) < 1e-9
            for ss in sug.span_suggestions
            for s in SAG_STANDARD
        )

    def test_cenario3_resolvido_flecha_extrema(self):
        """Poste sobrecarregado, irresolvível no range padrão, resolvido com flecha extrema.

        Usamos um vão que ainda sobrecarrega com sag=0.9 m mas não com sag=1.0 m.
        Tração-on-pole ≈ T × (8.5 / (9.9 - 0.7)) = T × 8.5/9.2
        Para limiar: queremos T_on_pole(sag=0.9) > 2000 E T_on_pole(sag=1.0) <= 2000.
        T(sag) = (weight × span²) / (8 × sag)
        T_on_pole(sag) = T(sag) × 8.5/9.2
        target_T = 2000 × 9.2 / 8.5 ≈ 2164.7 daN (tração bruta crítica)
        Com sag=0.9: T = peso × span² / 7.2 ≤ 2164.7 → peso×span² ≤ 15586
        Com sag=1.0: T = peso × span² / 8.0 ≤ 2164.7 → peso×span² ≤ 17318

        Então escolhemos peso×span² entre 15586 e 17318, ex: 16000.
        peso = 1.5 kg/m; span² = 16000/1.5 = 10667 → span ≈ 103.3 m.
        Usamos span=104 m:
          sag=0.9: T=(1.5×104²)/(8×0.9)=(1.5×10816)/7.2=16224/7.2=2253 daN > 2164 → overloaded
          sag=1.0: T=(1.5×10816)/8.0=16224/8.0=2028 daN < 2164 → OK
        """
        node = _node(1, pole_id=1)
        span = _span(1, src=1, tgt=2, mt_sag=0.1, span_m=104.0)
        conds = {1: _cond()}
        poles = {1: _pole(resistance=2000.0)}

        report = run_solver(1, [node, _node(2, pole_id=0, is_ghost=True)], [span], conds, poles)

        assert report.overloaded_count == 1
        assert report.solvable_count == 1
        assert report.requires_span_break_count == 0

        sug = report.suggestions[0]
        assert sug.is_extreme is True
        assert sug.requires_span_break is False
        assert sug.target_effort_dan is not None
        assert sug.target_effort_dan <= MAX_STRUCTURAL_DAN
        # Flecha sugerida deve estar no range extremo
        assert any(
            abs(ss.new_mt_sag_m - s) < 1e-9
            for ss in sug.span_suggestions
            for s in SAG_EXTREME
        )
        assert "extremo" in sug.message.lower() or "extreme" in sug.message.lower() or "atenção" in sug.message.lower()

    def test_cenario4_tracao_absurda_requires_span_break(self):
        """Tração absurda (>>2000 daN mesmo com flecha máxima) → requires_span_break=True."""
        # vão=500 m, sag_inicial=0.1m
        # sag=1.3 m (máximo): T=(1.5×500²)/(8×1.3)=375000/10.4=36057 daN >> 2000
        node = _node(1, pole_id=1)
        span = _span(1, src=1, tgt=2, mt_sag=0.1, span_m=500.0)
        conds = {1: _cond()}
        poles = {1: _pole(resistance=2000.0)}

        report = run_solver(1, [node, _node(2, pole_id=0, is_ghost=True)], [span], conds, poles)

        assert report.overloaded_count == 1
        assert report.solvable_count == 0
        assert report.requires_span_break_count == 1

        sug = report.suggestions[0]
        assert sug.requires_span_break is True
        assert sug.target_effort_dan is None
        assert "2000" in sug.message
        assert "quebra" in sug.message.lower()

    def test_no_fantasma_ignorado_pelo_solver(self):
        """Nós fantasmas (is_ghost=True) nunca entram na análise do solver."""
        ghost = _node(1, pole_id=1, is_ghost=True)
        span = _span(1, src=1, tgt=2, mt_sag=0.1, span_m=500.0)
        conds = {1: _cond()}
        poles = {1: _pole(resistance=2000.0)}

        report = run_solver(1, [ghost, _node(2, pole_id=0, is_ghost=True)], [span], conds, poles)

        assert report.overloaded_count == 0
        assert report.suggestions == []

    def test_no_sem_vaos_nao_gera_sugestao(self):
        """Nó sem vãos conectados → esforço=0, sem sugestão."""
        node = _node(1, pole_id=1)
        conds = {1: _cond()}
        poles = {1: _pole(resistance=2000.0)}

        report = run_solver(1, [node], [], conds, poles)

        assert report.overloaded_count == 0
        assert report.suggestions == []

    def test_multiplos_nos_mix_cenarios(self):
        """Relatório com múltiplos nós: um OK, um solvable, um requires_span_break."""
        n1 = _node(1, pole_id=1)                     # OK — vão normal
        n2 = _node(2, pole_id=1)                     # overloaded mas solvable
        n3 = _node(3, pole_id=1)                     # requires_span_break
        g4 = _node(4, pole_id=0, is_ghost=True)      # destino = rede existente
        g5 = _node(5, pole_id=0, is_ghost=True)
        g6 = _node(6, pole_id=0, is_ghost=True)

        spans = [
            _span(1, src=1, tgt=4, mt_sag=0.5, span_m=50.0),    # n1 OK
            _span(2, src=2, tgt=5, mt_sag=0.1, span_m=50.0),     # n2 overloaded / solvable
            _span(3, src=3, tgt=6, mt_sag=0.1, span_m=500.0),    # n3 requires_span_break
        ]
        conds = {1: _cond()}
        poles = {1: _pole(resistance=2000.0)}

        report = run_solver(1, [n1, n2, n3, g4, g5, g6], spans, conds, poles)

        assert report.overloaded_count == 2
        assert report.solvable_count == 1
        assert report.requires_span_break_count == 1
        assert len(report.suggestions) == 2

    def test_compute_effort_helper_sem_vaos(self):
        """_compute_effort retorna 0.0 quando não há vãos conectados."""
        node = _node(1)
        result = _compute_effort(node, [], {1: _cond()}, {1: _pole()})
        assert result == 0.0

    def test_compute_effort_com_bt_conductor(self):
        """_compute_effort considera vãos BT quando bt_conductor_id está preenchido."""
        node = _node(1, pole_id=1)
        bt_cond = Conductor(id=2, name="BT-Mock", diameter_m=0.012, weight_kg_m=0.3,
                            cable_qty=4, network_type="BT")
        span = NodeSpanConfig(
            id=1, source_node_id=1, target_node_id=2,
            bt_conductor_id=2, bt_sag_m=0.5, span_length_m=30.0, angle_deg=0.0,
        )
        effort = _compute_effort(node, [span], {2: bt_cond}, {1: _pole()})
        assert effort > 0.0


# ─── Testes de API ────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def solver_db_path():
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
            messenger_weight REAL DEFAULT 0, messenger_diameter REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS poles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT, height_m REAL, resistance_dan REAL, weight_parameter_x REAL DEFAULT 0
        );
        INSERT INTO poles (type_name, height_m, resistance_dan) VALUES ('DT-1000', 11, 1000);
        INSERT INTO conductors (name, diameter_m, weight_kg_m, cable_qty, network_type, messenger_weight, messenger_diameter)
            VALUES ('MT-Mock', 0.015, 0.5, 3, 'MT', 0, 0);
        INSERT INTO projects (name) VALUES ('Solver Test Project');
    """)
    conn.commit()
    conn.close()
    yield path
    try:
        os.remove(path)
    except PermissionError:
        pass


@pytest.fixture(scope="module")
def solver_client(solver_db_path):
    def override_get_db():
        conn = sqlite3.connect(solver_db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def override_get_repo():
        return ProjectRepository(db_path=solver_db_path)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_repository] = override_get_repo

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


class TestSolverAPI:
    def test_solve_project_not_found(self, solver_client):
        res = solver_client.get("/projects/99999/solve")
        assert res.status_code == 404

    def test_solve_empty_project_returns_empty_report(self, solver_client):
        res = solver_client.get("/projects/1/solve")
        assert res.status_code == 200
        data = res.json()
        assert data["overloaded_count"] == 0
        assert data["suggestions"] == []

    def test_solve_with_overloaded_node(self, solver_client, solver_db_path):
        """Cria P1 (real, sobrecarregado) e P2 (destino) com vão de 50m, sag=0.1m."""
        conn = sqlite3.connect(solver_db_path)
        conn.execute("INSERT INTO project_nodes (project_id, pole_id, label, is_ghost) VALUES (1, 1, 'P1', 0)")
        conn.execute("INSERT INTO project_nodes (project_id, pole_id, label, is_ghost) VALUES (1, 0, 'P2', 0)")
        conn.commit()
        p1_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0] - 1
        p2_id = p1_id + 1
        conn.execute(
            "INSERT INTO node_span_configs (source_node_id, target_node_id, mt_conductor_id, mt_sag_m, span_length_m, angle_deg) VALUES (?, ?, 1, 0.1, 50.0, 0.0)",
            (p1_id, p2_id)
        )
        conn.commit()
        conn.close()

        res = solver_client.get("/projects/1/solve")
        assert res.status_code == 200
        data = res.json()
        assert data["overloaded_count"] >= 1
        assert data["solvable_count"] >= 1

    def test_apply_suggestions_not_found(self, solver_client):
        res = solver_client.post("/projects/99999/solve/apply", json={"items": []})
        assert res.status_code == 404

    def test_apply_suggestions_updates_span(self, solver_client, solver_db_path):
        """Aplica uma sugestão de flecha e verifica que o banco foi atualizado."""
        conn = sqlite3.connect(solver_db_path)
        conn.execute("INSERT INTO project_nodes (project_id, pole_id, label) VALUES (1, 1, 'P-apply-src')")
        conn.execute("INSERT INTO project_nodes (project_id, pole_id, label) VALUES (1, 0, 'P-apply-tgt')")
        conn.commit()
        src_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0] - 1
        tgt_id = src_id + 1
        conn.execute(
            "INSERT INTO node_span_configs (source_node_id, target_node_id, mt_conductor_id, mt_sag_m, span_length_m) VALUES (?, ?, 1, 0.1, 50.0)",
            (src_id, tgt_id)
        )
        conn.commit()
        span_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()

        res = solver_client.post("/projects/1/solve/apply", json={
            "items": [{"span_suggestions": [{"span_id": span_id, "new_mt_sag_m": 0.8}]}]
        })
        assert res.status_code == 200
        assert res.json()["updated_spans"] == 1

        # Verifica o banco
        conn2 = sqlite3.connect(solver_db_path)
        row = conn2.execute("SELECT mt_sag_m FROM node_span_configs WHERE id=?", (span_id,)).fetchone()
        conn2.close()
        assert abs(row[0] - 0.8) < 1e-6

    def test_apply_empty_payload_returns_zero(self, solver_client):
        res = solver_client.post("/projects/1/solve/apply", json={"items": []})
        assert res.status_code == 200
        assert res.json()["updated_spans"] == 0
