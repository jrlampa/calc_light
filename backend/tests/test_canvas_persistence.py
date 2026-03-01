"""
test_canvas_persistence.py — Fase 23
Testes de integração para os endpoints de persistência do canvas React Flow.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_CANVAS = {
    "nodes": [
        {"id": "1", "type": "pole", "position": {"x": 100, "y": 200}, "data": {"label": "P1"}},
        {"id": "2", "type": "pole", "position": {"x": 300, "y": 200}, "data": {"label": "P2"}},
    ],
    "edges": [
        {"id": "e1-2", "source": "1", "target": "2"}
    ]
}


def _create_project(name: str = "Projeto Teste F23") -> int:
    """Helper: cria um projeto e retorna o ID."""
    resp = client.post("/projects/", json={"name": name})
    assert resp.status_code == 200
    return resp.json()["id"]


def test_save_canvas_returns_200():
    """PUT canvas deve retornar 200 com projeto existente."""
    pid = _create_project("Canvas Test Save")
    resp = client.put(f"/projects/{pid}/canvas", json=SAMPLE_CANVAS)
    assert resp.status_code == 200


def test_save_canvas_response_schema():
    """Resposta do PUT contém project_id, has_canvas e listas de nós/arestas."""
    pid = _create_project("Canvas Schema Test")
    resp = client.put(f"/projects/{pid}/canvas", json=SAMPLE_CANVAS)
    data = resp.json()
    assert data["project_id"] == pid
    assert data["has_canvas"] is True
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_load_canvas_after_save():
    """GET canvas deve retornar exatamente o que foi salvo."""
    pid = _create_project("Canvas Round-Trip Test")
    client.put(f"/projects/{pid}/canvas", json=SAMPLE_CANVAS)
    resp = client.get(f"/projects/{pid}/canvas")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_canvas"] is True
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    assert data["nodes"][0]["id"] == "1"


def test_load_canvas_empty_project():
    """GET canvas num projeto recém-criado retorna has_canvas=False e listas vazias."""
    pid = _create_project("Canvas Empty Test")
    resp = client.get(f"/projects/{pid}/canvas")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_canvas"] is False
    assert data["nodes"] == []
    assert data["edges"] == []


def test_save_canvas_nonexistent_project():
    """PUT canvas num projeto que não existe deve retornar 404."""
    resp = client.put("/projects/999999/canvas", json=SAMPLE_CANVAS)
    assert resp.status_code == 404


def test_load_canvas_nonexistent_project():
    """GET canvas num projeto que não existe deve retornar 404."""
    resp = client.get("/projects/999999/canvas")
    assert resp.status_code == 404
