"""
test_reports.py — Fase 24
Testes para o endpoint GET /api/v1/projects/{project_id}/report
e para as funções auxiliares de mapeamento do canvas.

Padrão: pytest + FastAPI TestClient + module-level SQLite fixture.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db, get_repository
from app.api.routers import reports as reports_module
from app.domain.electrical_models import (
    CqtOutputSchema,
    TrechoResultSchema,
)
from app.infrastructure.database.repository import ProjectRepository
from app.main import app

# ── Fixture: Banco de Dados em Tempfile ─────────────────────────────────────


@pytest.fixture(scope="module")
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)

    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Tabela projects com canvas_state (Fase 23)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            canvas_state    TEXT,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_nodes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            pole_id    INTEGER,
            label      TEXT,
            pos_x      REAL,
            pos_y      REAL,
            effort_dan REAL,
            is_ghost   INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS node_span_configs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            source_node_id   INTEGER NOT NULL,
            target_node_id   INTEGER NOT NULL,
            mt_conductor_id  INTEGER,
            mt_sag_m         REAL DEFAULT 0.0,
            bt_conductor_id  INTEGER,
            bt_sag_m         REAL DEFAULT 0.0,
            span_length_m    REAL DEFAULT 0.0,
            angle_deg        REAL DEFAULT 0.0
        )
    """)

    conn.commit()
    conn.close()

    yield path

    try:
        os.remove(path)
    except PermissionError:
        pass


@pytest.fixture(scope="module")
def client(temp_db_path):
    def override_get_db():
        conn = sqlite3.connect(temp_db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def override_get_repo():
        return ProjectRepository(db_path=temp_db_path)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_repository] = override_get_repo

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ── Helper para gravar canvas diretamente no DB ──────────────────────────────


def _save_canvas(db_path: str, project_id: int, canvas: dict) -> None:
    """Persiste canvas_state diretamente no banco de teste."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute(
        "UPDATE projects SET canvas_state = ? WHERE id = ?",
        (json.dumps(canvas, ensure_ascii=False), project_id),
    )
    conn.commit()
    conn.close()


# ── Mock de CqtOutputSchema ──────────────────────────────────────────────────


def _mock_cqt_output() -> CqtOutputSchema:
    trecho = TrechoResultSchema(
        id="P001",
        carga_kva=15.0,
        carga_acum_kva=15.0,
        dv_trecho_perc=0.85,
        dv_acum_perc=0.85,
        v_final=125.92,
        icc_amperes=3200.0,
        cable_temp_celsius=42.3,
        thermal_status="Ok !",
        status="Ok",
    )
    return CqtOutputSchema(
        lado_1=[trecho],
        lado_2=[],
        carga_atual_kva=15.0,
        carga_projetada_kva=17.25,
        trafo_loading_percent=15.3,
        trafo_status="Operação Normal",
    )


# ── Canvas válido para testes ────────────────────────────────────────────────


def _valid_canvas() -> dict:
    """Canvas mínimo válido: transformador + 1 poste + 1 aresta."""
    return {
        "nodes": [
            {
                "id": "trafo-1",
                "type": "pole",
                "position": {"x": 0, "y": 0},
                "data": {
                    "label": "Trafo",
                    "is_transformer": True,
                    "is_ghost": False,
                    "ramais": [],
                },
            },
            {
                "id": "pole-1",
                "type": "pole",
                "position": {"x": 100, "y": 0},
                "data": {
                    "label": "P001",
                    "is_transformer": False,
                    "is_ghost": False,
                    "ramais": [{"tipo": "53 AA", "qtd": 2}],
                },
            },
        ],
        "edges": [
            {
                "id": "edge-1",
                "source": "trafo-1",
                "target": "pole-1",
                "data": {
                    "condutor": "MULTIPLEX 3X35+25",
                    "comprimento": 50.0,
                    "fases": 3,
                    "tipo_trecho": "rede",
                },
            }
        ],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }


# ── Testes: Endpoints ────────────────────────────────────────────────────────


def test_report_project_not_found(client):
    """404 quando o projeto não existe no banco."""
    response = client.get("/api/v1/projects/99999/report")
    assert response.status_code == 404
    assert "não encontrado" in response.json()["detail"].lower()


def test_report_canvas_not_found(client, temp_db_path):
    """404 quando o projeto existe mas o canvas nunca foi salvo (canvas_state NULL)."""
    # Criar projeto sem salvar canvas
    res = client.post("/projects/", json={"name": "Projeto Sem Canvas"})
    assert res.status_code == 200
    p_id = res.json()["id"]

    response = client.get(f"/api/v1/projects/{p_id}/report")
    # canvas_state NULL → get_canvas_state retorna {} → status 422 (canvas vazio)
    # (nenhum projeto "novo" tem canvas_state preenchido)
    assert response.status_code in (404, 422)


def test_report_empty_canvas(client, temp_db_path):
    """422 quando o canvas foi salvo mas está vazio (sem nós)."""
    res = client.post("/projects/", json={"name": "Projeto Canvas Vazio"})
    p_id = res.json()["id"]

    # Salvar canvas vazio
    _save_canvas(temp_db_path, p_id, {"nodes": [], "edges": []})

    response = client.get(f"/api/v1/projects/{p_id}/report")
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "vazio" in detail.lower() or "canvas" in detail.lower()


def test_report_no_transformer(client, temp_db_path):
    """422 quando o canvas tem nós mas nenhum é transformador."""
    res = client.post("/projects/", json={"name": "Projeto Sem Transformador"})
    p_id = res.json()["id"]

    canvas = {
        "nodes": [
            {
                "id": "pole-1",
                "type": "pole",
                "position": {"x": 0, "y": 0},
                "data": {"label": "P001", "is_transformer": False, "is_ghost": False},
            }
        ],
        "edges": [],
    }
    _save_canvas(temp_db_path, p_id, canvas)

    response = client.get(f"/api/v1/projects/{p_id}/report")
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "transformador" in detail.lower()


def test_report_success_returns_pdf(client, temp_db_path):
    """200 com PDF válido quando canvas válido + serviço elétrico mockado."""
    res = client.post("/projects/", json={"name": "Projeto Memorial PDF"})
    p_id = res.json()["id"]

    _save_canvas(temp_db_path, p_id, _valid_canvas())

    mock_output = _mock_cqt_output()

    with patch.object(reports_module._service, "calcular_cqt_completo", return_value=mock_output):
        response = client.get(f"/api/v1/projects/{p_id}/report")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers.get("content-disposition", "")
    assert len(response.content) > 500  # PDF não pode ser vazio


# ── Testes: Funções de Mapeamento (Unitários) ────────────────────────────────


def test_canvas_nodes_to_graph_filters_ghost():
    """Nós fantasmas devem ser excluídos do grafo."""
    raw_nodes = [
        {
            "id": "trafo-1",
            "type": "pole",
            "data": {"label": "Trafo", "is_transformer": True, "is_ghost": False},
        },
        {
            "id": "ghost-1",
            "type": "pole",
            "data": {"label": "Fantasma", "is_transformer": False, "is_ghost": True},
        },
        {
            "id": "pole-1",
            "type": "pole",
            "data": {"label": "P001", "is_transformer": False, "is_ghost": False},
        },
    ]

    result = reports_module._canvas_nodes_to_graph(raw_nodes)

    ids = [n.id for n in result]
    assert "trafo-1" in ids
    assert "pole-1" in ids
    assert "ghost-1" not in ids, "Nó fantasma não deve aparecer no grafo"
    assert len(result) == 2


def test_canvas_nodes_to_graph_parses_ramais():
    """Ramais devem ser convertidos corretamente para RamalSchema."""
    raw_nodes = [
        {
            "id": "pole-1",
            "data": {
                "label": "P001",
                "is_transformer": False,
                "is_ghost": False,
                "ramais": [
                    {"tipo": " 53 aa ", "qtd": 3},
                    {"tipo": "33 AA", "qtd": 1},
                ],
            },
        }
    ]

    result = reports_module._canvas_nodes_to_graph(raw_nodes)
    assert len(result) == 1
    assert len(result[0].ramais) == 2
    assert result[0].ramais[0].tipo == "53 AA"  # stripped + upper
    assert result[0].ramais[0].qtd == 3


def test_canvas_edges_to_graph_cqt_format():
    """Arestas em formato CQT devem usar condutor/comprimento/fases."""
    raw_edges = [
        {
            "id": "edge-1",
            "source": "trafo-1",
            "target": "pole-1",
            "data": {
                "condutor": "MULTIPLEX 3X35+25",
                "comprimento": 75.0,
                "fases": 3,
                "tipo_trecho": "rede",
            },
        }
    ]

    result = reports_module._canvas_edges_to_graph(raw_edges)
    assert len(result) == 1
    edge = result[0]
    assert edge.condutor == "MULTIPLEX 3X35+25"
    assert edge.comprimento == 75.0
    assert edge.fases == 3
    assert edge.tipo_trecho == "rede"


def test_canvas_edges_to_graph_fallback_bt_conductor():
    """Sem condutor CQT, deve usar bt_conductor como fallback."""
    raw_edges = [
        {
            "id": "edge-1",
            "source": "trafo-1",
            "target": "pole-1",
            "data": {"bt_conductor": "53 QX", "span_length_m": 60.0},
        }
    ]

    result = reports_module._canvas_edges_to_graph(raw_edges)
    assert len(result) == 1
    assert result[0].condutor == "53 QX"
    assert result[0].comprimento == 60.0
    assert result[0].fases == 3  # fallback trifásico


def test_canvas_edges_to_graph_default_fallback():
    """Sem nenhum condutor ou comprimento, deve usar defaults."""
    raw_edges = [
        {
            "id": "edge-1",
            "source": "trafo-1",
            "target": "pole-1",
            "data": {},
        }
    ]

    result = reports_module._canvas_edges_to_graph(raw_edges)
    assert len(result) == 1
    assert result[0].condutor == "MULTIPLEX 3X35+25"  # default
    assert result[0].comprimento == 50.0              # default
    assert result[0].fases == 3                       # default


def test_canvas_edges_to_graph_skips_incomplete_edges():
    """Arestas sem source ou target devem ser ignoradas."""
    raw_edges = [
        {"id": "edge-bad", "source": "", "target": "pole-1", "data": {}},
        {"id": "edge-ok", "source": "trafo-1", "target": "pole-1", "data": {}},
    ]

    result = reports_module._canvas_edges_to_graph(raw_edges)
    assert len(result) == 1
    assert result[0].id == "edge-ok"
