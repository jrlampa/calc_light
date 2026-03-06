"""Testes de integração para os endpoints GIS (parse-file, import-nodes, outgoing-conductors).

Aumenta a cobertura do app.api.routers.gis de ~37% para >80%.
Todos os testes usam um SQLite temporário em disco com esquema completo.
"""

from __future__ import annotations

import io
import json
import os
import sqlite3
import tempfile
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db, get_repository
from app.infrastructure.database.repository import ProjectRepository
from app.main import app

# ─── Schema SQL mínimo para os testes ────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    enable_equipment_drag INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS project_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    pole_id INTEGER,
    label TEXT,
    pos_x REAL DEFAULT 0.0,
    pos_y REAL DEFAULT 0.0,
    effort_dan REAL DEFAULT 0.0,
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
    name TEXT, diameter_m REAL, weight_kg_m REAL, cable_qty INTEGER,
    network_type TEXT, messenger_weight REAL DEFAULT 0.0, messenger_diameter REAL DEFAULT 0.0
);
CREATE TABLE IF NOT EXISTS poles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name TEXT, height_m REAL, resistance_dan REAL, weight_parameter_x REAL DEFAULT 0.0
);
CREATE TABLE IF NOT EXISTS catalog_equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    area_arrasto_m2 REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS node_equipment (
    node_id INTEGER NOT NULL,
    equipment_id INTEGER NOT NULL,
    PRIMARY KEY (node_id, equipment_id)
);
"""


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def gis_db_path():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    # Seed: uma projeto, dois condutores, um poste
    conn.execute("INSERT INTO projects (name) VALUES ('Proj GIS')")
    conn.execute(
        "INSERT INTO conductors (name, diameter_m, weight_kg_m, cable_qty, network_type)"
        " VALUES ('MT-Test', 0.015, 0.5, 3, 'MT')"
    )
    conn.execute(
        "INSERT INTO poles (type_name, height_m, resistance_dan) VALUES ('DT-600', 11, 600)"
    )
    conn.commit()
    conn.close()
    yield path
    try:
        os.remove(path)
    except PermissionError:
        pass


@pytest.fixture(scope="module")
def gis_client(gis_db_path):
    def _db():
        c = sqlite3.connect(gis_db_path)
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    def _repo():
        return ProjectRepository(db_path=gis_db_path)

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_repository] = _repo
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ─── Helpers de dados de arquivo GIS ─────────────────────────────────────────

def _make_geojson(features: list[dict]) -> bytes:
    return json.dumps({"type": "FeatureCollection", "features": features}).encode()


def _make_kml(placemarks: list[dict]) -> bytes:
    inner = ""
    for pm in placemarks:
        name_part = f"<name>{pm.get('name', 'P')}</name>"
        coord_part = f"<Point><coordinates>{pm['coords']}</coordinates></Point>"
        inner += f"<Placemark>{name_part}{coord_part}</Placemark>"
    return (
        f'<?xml version="1.0"?>'
        f'<kml xmlns="http://www.opengis.net/kml/2.2"><Document>{inner}</Document></kml>'
    ).encode()


def _make_kmz(kml_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("doc.kml", kml_bytes)
    return buf.getvalue()


# ─── Testes: parse-file ───────────────────────────────────────────────────────


class TestParseFile:
    def test_parse_geojson_returns_points(self, gis_client):
        geojson = _make_geojson([
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-43.0, -22.0]},
                "properties": {"name": "Ponto 1"},
            }
        ])
        resp = gis_client.post(
            "/projects/1/parse-file",
            files={"file": ("test.geojson", geojson, "application/json")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["label"] == "Ponto 1"
        assert data[0]["lat"] == pytest.approx(-22.0)
        assert data[0]["lng"] == pytest.approx(-43.0)

    def test_parse_kml_returns_points(self, gis_client):
        kml = _make_kml([{"name": "Torre A", "coords": "-43.1,-22.1,0"}])
        resp = gis_client.post(
            "/projects/1/parse-file",
            files={"file": ("postes.kml", kml, "application/vnd.google-earth.kml+xml")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["label"] == "Torre A"

    def test_parse_kmz_returns_points(self, gis_client):
        kml = _make_kml([{"name": "KMZ-Node", "coords": "-44.0,-23.0,0"}])
        kmz = _make_kmz(kml)
        resp = gis_client.post(
            "/projects/1/parse-file",
            files={"file": ("postes.kmz", kmz, "application/octet-stream")},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_parse_invalid_extension_returns_400(self, gis_client):
        resp = gis_client.post(
            "/projects/1/parse-file",
            files={"file": ("postes.csv", b"lat,lng\n-22.0,-43.0", "text/csv")},
        )
        assert resp.status_code == 400

    def test_parse_malformed_json_returns_400(self, gis_client):
        resp = gis_client.post(
            "/projects/1/parse-file",
            files={"file": ("postes.geojson", b"NOT JSON AT ALL", "application/json")},
        )
        assert resp.status_code == 400

    def test_parse_project_not_found_returns_404(self, gis_client):
        geojson = _make_geojson([])
        resp = gis_client.post(
            "/projects/99999/parse-file",
            files={"file": ("test.geojson", geojson, "application/json")},
        )
        assert resp.status_code == 404


# ─── Testes: import-nodes ─────────────────────────────────────────────────────


class TestImportNodes:
    def test_import_nodes_happy_path(self, gis_client):
        payload = {
            "points": [
                {"label": "P-Import-1", "lat": -22.0, "lng": -43.0},
                {"label": "P-Import-2", "lat": -22.1, "lng": -43.1},
            ]
        }
        resp = gis_client.post("/projects/1/import-nodes", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all("id" in n and n["id"] is not None for n in data)
        assert data[0]["label"] == "P-Import-1"

    def test_import_empty_list_returns_400(self, gis_client):
        resp = gis_client.post("/projects/1/import-nodes", json={"points": []})
        assert resp.status_code == 400

    def test_import_project_not_found_returns_404(self, gis_client):
        payload = {"points": [{"label": "X", "lat": 0.0, "lng": 0.0}]}
        resp = gis_client.post("/projects/99999/import-nodes", json=payload)
        assert resp.status_code == 404

    def test_imported_nodes_have_grid_positions(self, gis_client):
        """Verifica que os nós importados recebem posições de grade (pos_x/pos_y)."""
        payload = {
            "points": [{"label": f"Grid-{i}", "lat": -22.0, "lng": -43.0} for i in range(3)]
        }
        resp = gis_client.post("/projects/1/import-nodes", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        # Todos devem ter pos_x e pos_y
        for node in data:
            assert "pos_x" in node
            assert "pos_y" in node


# ─── Testes: outgoing-conductors ─────────────────────────────────────────────


class TestOutgoingConductors:
    def _insert_node(self, db_path: str, project_id: int = 1) -> int:
        conn = sqlite3.connect(db_path)
        cur = conn.execute(
            "INSERT INTO project_nodes (project_id, pole_id, label) VALUES (?, 0, 'P')",
            (project_id,),
        )
        node_id = cur.lastrowid
        conn.commit()
        conn.close()
        return node_id

    def _insert_span(self, db_path: str, source: int, target: int, mt_id: int | None, mt_sag: float) -> None:
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO node_span_configs
               (source_node_id, target_node_id, mt_conductor_id, mt_sag_m, span_length_m, angle_deg)
               VALUES (?, ?, ?, ?, 50.0, 0.0)""",
            (source, target, mt_id, mt_sag),
        )
        conn.commit()
        conn.close()

    def test_returns_empty_when_no_span(self, gis_client, gis_db_path):
        nid = self._insert_node(gis_db_path)
        resp = gis_client.get(f"/projects/1/nodes/{nid}/outgoing-conductors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mt_conductor_id"] is None
        assert data["bt_conductor_id"] is None

    def test_returns_conductor_when_span_exists(self, gis_client, gis_db_path):
        src = self._insert_node(gis_db_path)
        tgt = self._insert_node(gis_db_path)
        self._insert_span(gis_db_path, src, tgt, mt_id=1, mt_sag=0.7)

        resp = gis_client.get(f"/projects/1/nodes/{src}/outgoing-conductors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mt_conductor_id"] == 1
        assert data["mt_sag_m"] == pytest.approx(0.7)

    def test_project_not_found_returns_404(self, gis_client):
        resp = gis_client.get("/projects/99999/nodes/1/outgoing-conductors")
        assert resp.status_code == 404
