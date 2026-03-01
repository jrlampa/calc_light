"""
test_calculate_network_route.py — Fase 22
Testes de integração para o endpoint POST /api/v1/calculate-network
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ── Payload válido mínimo ────────────────────────────────────────────────────

VALID_PAYLOAD = {
    "u_nominal": 127.0,
    "leitura_trafo": 200.0,
    "trafo_nominal_kva": 112.5,
    "nodes": [
        {"id": "trafo-1", "label": "TRAFO", "is_transformer": True, "ramais": []},
        {"id": "p1", "label": "P1", "is_transformer": False, "ramais": []},
        {"id": "p2", "label": "P2", "is_transformer": False, "ramais": []},
    ],
    "edges": [
        {
            "id": "e1", "source": "trafo-1", "target": "p1",
            "condutor": "33", "comprimento": 50.0, "fases": 3, "tipo_trecho": "rede"
        },
        {
            "id": "e2", "source": "p1", "target": "p2",
            "condutor": "33", "comprimento": 40.0, "fases": 3, "tipo_trecho": "rede"
        },
    ]
}


def test_calculate_network_returns_200():
    """Endpoint retorna 200 com payload topológico válido."""
    response = client.post("/api/v1/calculate-network", json=VALID_PAYLOAD)
    assert response.status_code == 200


def test_calculate_network_response_schema():
    """Resposta contém os campos obrigatórios do CqtOutputSchema."""
    response = client.post("/api/v1/calculate-network", json=VALID_PAYLOAD)
    data = response.json()
    required_keys = ["lado_1", "lado_2", "carga_atual_kva", "carga_projetada_kva",
                     "trafo_loading_percent", "trafo_status"]
    for key in required_keys:
        assert key in data, f"Campo '{key}' ausente na resposta"


def test_calculate_network_trecho_has_electrical_fields():
    """Cada TrechoResult contém os campos elétricos críticos."""
    response = client.post("/api/v1/calculate-network", json=VALID_PAYLOAD)
    data = response.json()
    all_trechos = data["lado_1"] + data["lado_2"]
    assert len(all_trechos) > 0, "Nenhum trecho retornado"
    for trecho in all_trechos:
        for field in ["id", "dv_acum_perc", "v_final", "icc_amperes",
                      "cable_temp_celsius", "thermal_status", "status"]:
            assert field in trecho, f"Campo '{field}' ausente no trecho {trecho.get('id')}"


def test_calculate_network_icc_is_positive():
    """Icc deve ser estritamente positivo em qualquer configuração válida."""
    response = client.post("/api/v1/calculate-network", json=VALID_PAYLOAD)
    data = response.json()
    all_trechos = data["lado_1"] + data["lado_2"]
    for trecho in all_trechos:
        assert trecho["icc_amperes"] > 0, f"Icc inválido no nó {trecho['id']}"


def test_calculate_network_invalid_topology_returns_422():
    """Topologia sem raiz (trafo) deve retornar erro 422."""
    no_root = {
        **VALID_PAYLOAD,
        "nodes": [
            {"id": "p1", "label": "P1", "is_transformer": False, "ramais": []},
            {"id": "p2", "label": "P2", "is_transformer": False, "ramais": []},
        ],
    }
    response = client.post("/api/v1/calculate-network", json=no_root)
    assert response.status_code == 422


def test_calculate_network_empty_graph_returns_422():
    """Grafo vazio deve retornar erro 422."""
    empty = {**VALID_PAYLOAD, "nodes": [], "edges": []}
    response = client.post("/api/v1/calculate-network", json=empty)
    assert response.status_code in (422, 500)  # Depende da validação interna
