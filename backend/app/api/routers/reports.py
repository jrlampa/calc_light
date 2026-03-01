"""
reports.py — Fase 24
GET /api/v1/projects/{project_id}/report

Fluxo (Smart Backend — DDD):
  DB.canvas_state (React Flow JSON)
    → _build_graph_payload()     (mapeamento RF → GraphPayloadSchema)
    → TopologyParser              (validação + bifurcação topológica)
    → LightElectricalService      (motor CQT V8: ΔV%, Icc, T°, trafo)
    → generate_memorial_pdf()    (ReportLab Platypus — Fase 24)
    → StreamingResponse          (application/pdf, attachment)
"""

from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_repository
from app.domain.electrical_models import (
    GraphEdgeSchema,
    GraphNodeSchema,
    GraphPayloadSchema,
    RamalSchema,
)
from app.domain.electrical_services import LightElectricalService
from app.domain.topology_parser import TopologyError, TopologyParser
from app.infrastructure.database.repository import ProjectRepository
from app.services.pdf_generator import generate_memorial_pdf

router = APIRouter(prefix="/api/v1/projects", tags=["Reports"])

# Instâncias reutilizáveis (sem estado mutável — seguras para reuso entre requests)
_parser = TopologyParser()
_service = LightElectricalService()


# ── Funções de Mapeamento Canvas → Graph ────────────────────────────────────


def _canvas_nodes_to_graph(raw_nodes: list[dict]) -> list[GraphNodeSchema]:
    """
    Converte os nós do canvas_state (formato React Flow) para GraphNodeSchema.

    Estrutura esperada de um nó React Flow:
        {
            "id": "node-1",
            "type": "pole",
            "position": {"x": ..., "y": ...},
            "data": {
                "label": "P001",
                "is_transformer": false,
                "is_ghost": false,
                "ramais": [{"tipo": "33 AA", "qtd": 2}]
            }
        }

    Nós fantasmas (is_ghost=True) são excluídos — não fazem parte da cadeia CQT.
    """
    graph_nodes: list[GraphNodeSchema] = []

    for node in raw_nodes:
        node_id = node.get("id", "")
        if not node_id:
            continue

        data = node.get("data") or {}

        # Excluir nós fantasmas (rede existente no entorno)
        if data.get("is_ghost", False):
            continue

        # Construir ramais
        ramais: list[RamalSchema] = []
        for r in (data.get("ramais") or []):
            try:
                ramais.append(
                    RamalSchema(tipo=str(r.get("tipo", "")).strip(), qtd=int(r.get("qtd", 0)))
                )
            except (ValueError, TypeError):
                continue

        graph_nodes.append(
            GraphNodeSchema(
                id=node_id,
                label=str(data.get("label", node_id)),
                is_transformer=bool(data.get("is_transformer", False)),
                ramais=ramais,
            )
        )

    return graph_nodes


def _canvas_edges_to_graph(raw_edges: list[dict]) -> list[GraphEdgeSchema]:
    """
    Converte as arestas do canvas_state (formato React Flow) para GraphEdgeSchema.

    Suporta dois formatos de aresta:
      - CQT canvas: data.condutor, data.comprimento, data.fases, data.tipo_trecho
      - Mechanical canvas: data.bt_conductor, data.mt_conductor, data.span_length_m

    Prioridade para condutor: condutor > bt_conductor > mt_conductor > fallback
    Prioridade para comprimento: comprimento > span_length_m > fallback (50 m)
    Prioridade para fases: data.fases > padrão 3 (trifásico BT Light)
    """
    graph_edges: list[GraphEdgeSchema] = []

    for edge in raw_edges:
        edge_id = edge.get("id", "")
        source  = edge.get("source", "")
        target  = edge.get("target", "")

        if not (edge_id and source and target):
            continue

        data = edge.get("data") or {}

        # Condutor: CQT format primeiro, depois mechanical BT, depois MT, depois default
        condutor = (
            data.get("condutor")
            or data.get("bt_conductor")
            or data.get("mt_conductor")
            or "MULTIPLEX 3X35+25"
        )
        condutor = str(condutor).strip()

        # Comprimento em metros
        raw_comp = (
            data.get("comprimento")
            or data.get("span_length_m")
            or edge.get("span_length_m")
            or 50.0
        )
        try:
            comprimento = float(raw_comp)
        except (ValueError, TypeError):
            comprimento = 50.0

        # Fases: padrão trifásico BT (Light distribui 3F na rede principal)
        try:
            fases = int(data.get("fases", 3))
        except (ValueError, TypeError):
            fases = 3
        fases = max(1, min(3, fases))

        tipo_trecho = str(data.get("tipo_trecho", "rede"))

        graph_edges.append(
            GraphEdgeSchema(
                id=edge_id,
                source=source,
                target=target,
                condutor=condutor,
                comprimento=comprimento,
                fases=fases,
                tipo_trecho=tipo_trecho,
            )
        )

    return graph_edges


def _build_graph_payload(canvas: dict) -> GraphPayloadSchema:
    """
    Constrói GraphPayloadSchema a partir do canvas_state salvo no banco.

    Parâmetros elétricos globais: usa defaults do schema se não salvos no canvas.
    Um campo opcional 'electrical_params' pode estar presente no canvas_state
    (para compatibilidade futura) com keys: u_nominal, leitura_trafo, trafo_nominal_kva.
    """
    params = canvas.get("electrical_params") or {}

    return GraphPayloadSchema(
        u_nominal=float(params.get("u_nominal", 127.0)),
        leitura_trafo=float(params.get("leitura_trafo", 0.0)),
        trafo_nominal_kva=float(params.get("trafo_nominal_kva", 112.5)),
        nodes=_canvas_nodes_to_graph(canvas.get("nodes") or []),
        edges=_canvas_edges_to_graph(canvas.get("edges") or []),
    )


# ── Endpoint ─────────────────────────────────────────────────────────────────


@router.get("/{project_id}/report", summary="Gerar Memorial de Cálculo (PDF)")
def get_project_report(
    project_id: int,
    repo: ProjectRepository = Depends(get_repository),
) -> StreamingResponse:
    """
    Gera e retorna o Memorial de Cálculo Técnico em PDF para o projeto.

    O PDF contém:
    - Cabeçalho de identificação (projeto, data, transformador, norma)
    - Resumo do transformador (kVA, carga atual, projeção, carregamento %)
    - Tabela de trechos do Lado 1 (ΔV%, Icc, temperatura, status)
    - Tabela de trechos do Lado 2 (idem)
    - Notas técnicas de referência normativa

    Reprocessa a matemática no motor V8 para garantir dados frescos.
    """

    # ── 1. Carregar projeto ──────────────────────────────────────────────────
    project = repo.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    # ── 2. Carregar canvas_state ─────────────────────────────────────────────
    canvas = repo.get_canvas_state(project_id)

    # get_canvas_state retorna None se o projeto não existe no DB
    if canvas is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado no banco.")

    # get_canvas_state retorna {} se o canvas nunca foi salvo
    if not canvas or not canvas.get("nodes"):
        raise HTTPException(
            status_code=422,
            detail=(
                "Canvas vazio: salve o diagrama antes de gerar o memorial. "
                "Use o botão 'Guardar' na barra de persistência do canvas."
            ),
        )

    # ── 3. Converter canvas → GraphPayloadSchema ─────────────────────────────
    try:
        payload = _build_graph_payload(canvas)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Erro ao interpretar o canvas: {exc}",
        ) from exc

    # Validar presença de transformador
    if not any(n.is_transformer for n in payload.nodes):
        raise HTTPException(
            status_code=422,
            detail=(
                "Nenhum transformador encontrado no canvas. "
                "Adicione um nó transformador e salve o canvas antes de gerar o memorial."
            ),
        )

    # ── 4. Parser de topologia ───────────────────────────────────────────────
    try:
        cqt_input = _parser.parse_to_cqt_input(payload)
    except TopologyError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Topologia inválida: {exc}",
        ) from exc

    # ── 5. Motor CQT V8 ──────────────────────────────────────────────────────
    try:
        cqt_output = _service.calcular_cqt_completo(cqt_input)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro no motor elétrico: {exc}",
        ) from exc

    # ── 6. Geração do PDF ────────────────────────────────────────────────────
    try:
        pdf_bytes = generate_memorial_pdf(
            project_name=project.name,
            created_at=project.created_at or "",
            trafo_nominal_kva=cqt_input.trafo_nominal_kva,
            cqt_output=cqt_output,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na geração do PDF: {exc}",
        ) from exc

    # ── 7. StreamingResponse ─────────────────────────────────────────────────
    # Sanitizar nome do projeto para uso seguro em Content-Disposition
    safe_name = "".join(
        c if (c.isalnum() or c in "-_") else "_" for c in project.name
    )
    filename = f"memorial_cqt_projeto_{project_id}_{safe_name}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
