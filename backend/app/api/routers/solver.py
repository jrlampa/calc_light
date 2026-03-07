"""Router do Solver Global — Fase 17.

Rotas:
  GET  /projects/{project_id}/solve          → executa heurística, retorna SolverReport
  POST /projects/{project_id}/solve/apply    → aplica as sugestões escolhidas pelo usuário
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_db, get_repository
from app.domain.models import Conductor, Pole
from app.domain.solver import SolverReport, SolverSuggestion, run_solver
from app.infrastructure.database.repository import ProjectRepository

router = APIRouter(prefix="/projects", tags=["Solver"])


# ─── Schemas de Resposta / Entrada ────────────────────────────────────────────


class SpanSuggestionOut(BaseModel):
    span_id: int
    new_mt_sag_m: float | None = None
    new_bt_sag_m: float | None = None


class SolverSuggestionOut(BaseModel):
    node_id: int
    node_label: str
    current_effort_dan: float
    target_effort_dan: float | None = None
    is_extreme: bool
    requires_span_break: bool
    message: str
    span_suggestions: list[SpanSuggestionOut]


class SolverReportOut(BaseModel):
    project_id: int
    suggestions: list[SolverSuggestionOut]
    overloaded_count: int
    solvable_count: int
    requires_span_break_count: int


class ApplySuggestionRequest(BaseModel):
    """Payload para aplicar UMA sugestão (as solvables, not span_break ones)."""
    span_suggestions: list[SpanSuggestionOut]


class ApplyBulkRequest(BaseModel):
    """Payload para aplicar múltiplas sugestões em lote."""
    items: list[ApplySuggestionRequest]


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _to_out(s: SolverSuggestion) -> SolverSuggestionOut:
    return SolverSuggestionOut(
        node_id=s.node_id,
        node_label=s.node_label,
        current_effort_dan=s.current_effort_dan,
        target_effort_dan=s.target_effort_dan,
        is_extreme=s.is_extreme,
        requires_span_break=s.requires_span_break,
        message=s.message,
        span_suggestions=[
            SpanSuggestionOut(
                span_id=ss.span_id,
                new_mt_sag_m=ss.new_mt_sag_m,
                new_bt_sag_m=ss.new_bt_sag_m,
            )
            for ss in s.span_suggestions
        ],
    )


def _report_to_out(r: SolverReport) -> SolverReportOut:
    return SolverReportOut(
        project_id=r.project_id,
        suggestions=[_to_out(s) for s in r.suggestions],
        overloaded_count=r.overloaded_count,
        solvable_count=r.solvable_count,
        requires_span_break_count=r.requires_span_break_count,
    )


# ─── Rotas ───────────────────────────────────────────────────────────────────


@router.get("/{project_id}/solve", response_model=SolverReportOut)
def solve_project(
    project_id: int,
    db: sqlite3.Connection = Depends(get_db),
    repo: ProjectRepository = Depends(get_repository),
):
    """Executa o Motor de Otimização Heurística para o projeto.

    Retorna um relatório com sugestões de ajuste de flecha por poste sobrecarregado.
    Postes com esforço > 2000 daN irresolvível recebem requires_span_break=True.
    """
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    nodes = repo.get_project_nodes(project_id)
    spans = repo.get_span_configs_for_project(project_id)

    c_rows = db.execute("SELECT * FROM conductors").fetchall()
    conductors = {row["id"]: Conductor(**dict(row)) for row in c_rows}

    p_rows = db.execute("SELECT * FROM poles").fetchall()
    poles = {row["id"]: Pole(**dict(row)) for row in p_rows}

    report = run_solver(project_id, nodes, spans, conductors, poles)
    return _report_to_out(report)


@router.post("/{project_id}/solve/apply", response_model=dict)
def apply_solver_suggestions(
    project_id: int,
    payload: ApplyBulkRequest,
    repo: ProjectRepository = Depends(get_repository),
):
    """Aplica as sugestões de flecha selecionadas pelo usuário (Human-in-the-loop).

    Cada item do payload contém uma lista de SpanSuggestion com os novos valores de flecha.
    Apenas vãos com new_mt_sag_m ou new_bt_sag_m preenchidos são atualizados.
    Retorna o número de vãos efetivamente modificados.
    """
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    updated = 0
    for item in payload.items:
        for ss in item.span_suggestions:
            if ss.new_mt_sag_m is not None or ss.new_bt_sag_m is not None:
                ok = repo.update_span_sag(ss.span_id, ss.new_mt_sag_m, ss.new_bt_sag_m)
                if ok:
                    updated += 1

    return {"updated_spans": updated, "message": f"{updated} vão(s) atualizado(s) com sucesso."}
