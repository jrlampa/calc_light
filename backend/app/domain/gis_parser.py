"""Motor de parsing de arquivos geoespaciais (KML, KMZ, GeoJSON, Excel).

Usa apenas bibliotecas stdlib (json, xml.etree, zipfile, io) e openpyxl para Excel.
Nenhuma dependência C++ (GDAL/Shapely/Fiona) é necessária.

Retorna uma lista uniforme de ParsedPoint independente do formato de entrada.
"""

from __future__ import annotations

import io
import json
import xml.etree.ElementTree as ET
import zipfile
from typing import Any

import openpyxl
from pydantic import BaseModel

_KML_NS = "http://www.opengis.net/kml/2.2"


class ParsedPoint(BaseModel):
    """Representa um ponto geoespacial extraído de um arquivo GIS."""

    label: str
    lat: float
    lng: float


# ─── Helpers internos ────────────────────────────────────────────────────────


def _kml_coords_to_latlon(coord_text: str) -> tuple[float, float]:
    """Converte a string KML 'lng,lat[,alt]' para (lat, lng).

    Raises:
        ValueError: Se o formato da coordenada for inválido.
    """
    parts = coord_text.strip().split(",")
    if len(parts) < 2:
        raise ValueError(f"Coordenada KML inválida: {coord_text!r}")
    return float(parts[1]), float(parts[0])


def _find_col(header: list[str], candidates: list[str]) -> int | None:
    """Retorna o índice da primeira coluna cujo nome (minúsculo) esteja em candidates."""
    for cand in candidates:
        if cand in header:
            return header.index(cand)
    return None


def _parse_kml_tree(root: ET.Element) -> list[ParsedPoint]:
    """Extrai Placemarks de uma árvore KML já parseada (com ou sem namespace)."""
    ns = {"kml": _KML_NS}
    placemarks = root.findall(".//kml:Placemark", ns)
    if not placemarks:
        placemarks = root.findall(".//Placemark")

    points: list[ParsedPoint] = []
    for pm in placemarks:
        name_el = pm.find("kml:name", ns)
        if name_el is None:
            name_el = pm.find("name")
        label = name_el.text.strip() if (name_el is not None and name_el.text) else "Ponto"

        coords_el = pm.find(".//kml:Point/kml:coordinates", ns)
        if coords_el is None:
            coords_el = pm.find(".//Point/coordinates")
        if coords_el is None or not coords_el.text:
            continue

        try:
            lat, lng = _kml_coords_to_latlon(coords_el.text)
        except ValueError:
            continue

        points.append(ParsedPoint(label=label, lat=lat, lng=lng))

    return points


# ─── Parsers por formato ─────────────────────────────────────────────────────


def parse_kml(content: bytes) -> list[ParsedPoint]:
    """Parseia bytes de um arquivo .kml e retorna lista de ParsedPoint.

    Raises:
        ValueError: Se o XML for malformado.
    """
    try:
        root = ET.fromstring(content.decode("utf-8", errors="replace"))
    except ET.ParseError as exc:
        raise ValueError(f"KML inválido: {exc}") from exc
    return _parse_kml_tree(root)


def parse_kmz(content: bytes) -> list[ParsedPoint]:
    """Parseia bytes de um arquivo .kmz (ZIP + KML) e retorna lista de ParsedPoint.

    Raises:
        ValueError: Se o arquivo não for um ZIP válido ou não contiver .kml.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
            if not kml_names:
                raise ValueError("Nenhum arquivo .kml encontrado dentro do .kmz")
            kml_bytes = zf.read(kml_names[0])
    except zipfile.BadZipFile as exc:
        raise ValueError(f"KMZ inválido (não é um arquivo ZIP): {exc}") from exc
    return parse_kml(kml_bytes)


def parse_geojson(content: bytes) -> list[ParsedPoint]:
    """Parseia bytes de um arquivo .geojson e retorna lista de ParsedPoint.

    Raises:
        ValueError: Se o JSON for inválido ou não respeitar o esquema GeoJSON.
    """
    try:
        data: Any = json.loads(content.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"GeoJSON inválido: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("GeoJSON deve ser um objeto JSON (dict), não uma lista ou primitivo")

    features = data.get("features", [])
    if not isinstance(features, list):
        raise ValueError("Campo 'features' do GeoJSON deve ser uma lista")

    points: list[ParsedPoint] = []
    for feat in features:
        if not isinstance(feat, dict):
            continue

        geom = feat.get("geometry") or {}
        props = feat.get("properties") or {}

        if geom.get("type") != "Point":
            continue

        coords = geom.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            continue

        try:
            lng, lat = float(coords[0]), float(coords[1])
        except (TypeError, ValueError):
            continue

        label = (
            props.get("name")
            or props.get("label")
            or props.get("Name")
            or "Ponto"
        )
        points.append(ParsedPoint(label=str(label), lat=lat, lng=lng))

    return points


def parse_excel(content: bytes) -> list[ParsedPoint]:
    """Parseia bytes de um arquivo .xlsx e retorna lista de ParsedPoint.

    Espera colunas (case-insensitive): label/name/nome, lat/latitude, lng/lon/longitude.

    Raises:
        ValueError: Se o arquivo for inválido, não tiver aba ativa ou faltar colunas obrigatórias.
    """
    buf = io.BytesIO(content)
    try:
        wb = openpyxl.load_workbook(buf, read_only=True)
    except Exception as exc:
        raise ValueError(f"Excel inválido: {exc}") from exc

    try:
        ws = wb.active
        if ws is None:
            raise ValueError("Planilha Excel não possui aba ativa")
        rows = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()
        buf.close()

    if not rows:
        raise ValueError("Planilha Excel vazia")

    header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
    label_col = _find_col(header, ["label", "name", "nome"])
    lat_col = _find_col(header, ["lat", "latitude"])
    lng_col = _find_col(header, ["lng", "lon", "longitude"])

    if lat_col is None or lng_col is None:
        raise ValueError(
            "Planilha Excel deve ter colunas 'lat'/'latitude' e 'lng'/'lon'/'longitude'"
        )

    points: list[ParsedPoint] = []
    for row in rows[1:]:
        try:
            lat = float(row[lat_col])
            lng = float(row[lng_col])
        except (TypeError, ValueError, IndexError):
            continue

        if label_col is not None and label_col < len(row) and row[label_col] is not None:
            label = str(row[label_col]).strip() or "Ponto"
        else:
            label = "Ponto"

        points.append(ParsedPoint(label=label, lat=lat, lng=lng))

    return points


# ─── Dispatcher público ──────────────────────────────────────────────────────

_PARSERS: dict[str, Any] = {
    ".kml": parse_kml,
    ".kmz": parse_kmz,
    ".geojson": parse_geojson,
    ".json": parse_geojson,
    ".xlsx": parse_excel,
    ".xls": parse_excel,
}


def parse_file(filename: str, content: bytes) -> list[ParsedPoint]:
    """Dispatcha o parsing baseado na extensão do arquivo.

    Args:
        filename: Nome original do arquivo (usado para detectar a extensão).
        content: Bytes do arquivo a ser parseado.

    Returns:
        Lista de ParsedPoint extraídos do arquivo.

    Raises:
        ValueError: Se a extensão não for suportada ou o conteúdo for inválido.
    """
    suffix = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    parser = _PARSERS.get(suffix)
    if parser is None:
        supported = ", ".join(_PARSERS)
        raise ValueError(f"Extensão '{suffix}' não suportada. Use: {supported}")
    return parser(content)
