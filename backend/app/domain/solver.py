"""Motor de Otimização Heurística — Fase 17 (Solver Global).

Regras de Negócio:
- Catálogo: mínimo 300 daN, teto estrutural 2000 daN.
- Flecha Padrão: 0.5 m.
- Range padrão: 0.3 m a 0.9 m (step 0.1).
- Range extremo: 1.0 m a 1.3 m (step 0.1) — is_extreme=True.
- Se nenhuma flecha (mesmo extrema) baixar o esforço para ≤ 2000 daN →
  requires_span_break=True (impossível resolver via flecha; necessária quebra de vão).

O solver itera sobre os postes REAIS sobrecarregados (is_ghost=False) e tenta aumentar
a flecha dos vãos conectados, reduzindo a tração T = (peso × vão²) / (8 × flecha).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .calculators import calculate_level_resultant
from .models import CalculationInput, Conductor, NodeSpanConfig, Pole, ProjectNode

# ─── Constantes do Catálogo ───────────────────────────────────────────────────

MIN_CAPACITY_DAN: float = 300.0    # mínimo catálogo (daN)
MAX_STRUCTURAL_DAN: float = 2000.0  # teto estrutural absoluto (daN)

# Flechas a tentar — padrão primeiro, depois extremas
SAG_STANDARD: list[float] = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
SAG_EXTREME: list[float] = [1.0, 1.1, 1.2, 1.3]


# ─── DTOs de Resultado ────────────────────────────────────────────────────────

@dataclass
class SpanSuggestion:
    span_id: int
    new_mt_sag_m: float | None = None
    new_bt_sag_m: float | None = None


@dataclass
class SolverSuggestion:
    node_id: int
    node_label: str
    current_effort_dan: float
    target_effort_dan: float | None = None
    is_extreme: bool = False
    requires_span_break: bool = False
    message: str = ""
    span_suggestions: list[SpanSuggestion] = field(default_factory=list)


@dataclass
class SolverReport:
    project_id: int
    suggestions: list[SolverSuggestion] = field(default_factory=list)
    overloaded_count: int = 0
    solvable_count: int = 0
    requires_span_break_count: int = 0


# ─── Função auxiliar: altura do poste ────────────────────────────────────────

def _pole_height(poles: dict[int, Pole], pole_id: int) -> float:
    pole = poles.get(pole_id)
    return pole.height_m if pole else 9.0


# ─── Função auxiliar: computa esforço de um nó com uma flecha sobreposta ─────

def _compute_effort(
    node: ProjectNode,
    spans: list[NodeSpanConfig],
    conductors: dict[int, Conductor],
    poles: dict[int, Pole],
    mt_sag_override: float | None = None,
    bt_sag_override: float | None = None,
) -> float:
    """Calcula o esforço total (daN) no nó com flechas opcionalmente sobrescritas.

    Se mt_sag_override não for None, aplica esse valor a todos os vãos MT do nó.
    Análogo para bt_sag_override.
    """
    inputs: list[CalculationInput] = []
    conds: list[Conductor] = []
    node_h = _pole_height(poles, node.pole_id)

    for span in spans:
        if span.source_node_id != node.id and span.target_node_id != node.id:
            continue

        is_source = span.source_node_id == node.id
        base_angle = span.angle_deg if is_source else (span.angle_deg + 180) % 360

        mt_cond = conductors.get(span.mt_conductor_id)
        bt_cond = conductors.get(span.bt_conductor_id)

        if mt_cond and mt_cond.id:
            sag = mt_sag_override if mt_sag_override is not None else span.mt_sag_m
            inputs.append(CalculationInput(
                span_m=span.span_length_m,
                sag_m=sag,
                angle_deg=base_angle,
                pole_height_m=node_h,
                anchorage_height_m=8.5,
                conductor_id=mt_cond.id,
                level="MT1",
                level_order=1,
            ))
            conds.append(mt_cond)

        if bt_cond and bt_cond.id:
            sag = bt_sag_override if bt_sag_override is not None else span.bt_sag_m
            inputs.append(CalculationInput(
                span_m=span.span_length_m,
                sag_m=sag,
                angle_deg=base_angle,
                pole_height_m=node_h,
                anchorage_height_m=7.0,
                conductor_id=bt_cond.id,
                level="BT",
                level_order=3,
            ))
            conds.append(bt_cond)

    if not inputs:
        return 0.0

    mt_in = [i for i in inputs if i.level == "MT1"]
    mt_co = [c for i, c in zip(inputs, conds, strict=False) if i.level == "MT1"]
    bt_in = [i for i in inputs if i.level == "BT"]
    bt_co = [c for i, c in zip(inputs, conds, strict=False) if i.level == "BT"]

    total = 0.0
    if mt_in:
        total += calculate_level_resultant(mt_in, mt_co).traction_on_pole_dan
    if bt_in:
        total += calculate_level_resultant(bt_in, bt_co).traction_on_pole_dan
    return round(total, 2)


# ─── Motor Principal ──────────────────────────────────────────────────────────

def run_solver(
    project_id: int,
    nodes: list[ProjectNode],
    spans: list[NodeSpanConfig],
    conductors: dict[int, Conductor],
    poles: dict[int, Pole],
) -> SolverReport:
    """Executa a heurística de otimização de flechas para o projeto.

    Para cada nó real sobrecarregado (esforço > 2000 daN ou > capacidade nominal):
      1. Tenta reduzir o esforço aumentando a flecha MT no range padrão (0.3–0.9 m).
      2. Se não conseguir, tenta o range extremo (1.0–1.3 m) com is_extreme=True.
      3. Se ainda assim impossível, retorna requires_span_break=True.

    Retorna um SolverReport com uma SolverSuggestion por nó problemático.
    """
    report = SolverReport(project_id=project_id)

    for node in nodes:
        if node.is_ghost:
            continue  # fantasmas nunca são calculados

        pole_obj = poles.get(node.pole_id)
        nominal = pole_obj.resistance_dan if pole_obj and pole_obj.resistance_dan > 0 else 0.0
        threshold = min(nominal, MAX_STRUCTURAL_DAN) if nominal > 0 else MAX_STRUCTURAL_DAN

        current_effort = _compute_effort(node, spans, conductors, poles)

        if current_effort <= threshold:
            continue  # poste OK, sem sugestão necessária

        report.overloaded_count += 1

        # Identifica os vãos conectados ao nó para montar span_suggestions
        connected_spans = [
            s for s in spans
            if s.source_node_id == node.id or s.target_node_id == node.id
        ]

        # Tenta cada flecha — padrão primeiro, depois extrema
        solved = False
        for sag_list, is_ext in [(SAG_STANDARD, False), (SAG_EXTREME, True)]:
            for sag in sag_list:
                trial_effort = _compute_effort(node, spans, conductors, poles, mt_sag_override=sag)
                if trial_effort <= MAX_STRUCTURAL_DAN:
                    span_sugs = [
                        SpanSuggestion(
                            span_id=s.id,
                            new_mt_sag_m=sag if s.mt_conductor_id else None,
                            new_bt_sag_m=None,  # BT não é ajustado nesta fase
                        )
                        for s in connected_spans
                        if s.id is not None
                    ]
                    report.suggestions.append(SolverSuggestion(
                        node_id=node.id,
                        node_label=node.label,
                        current_effort_dan=current_effort,
                        target_effort_dan=trial_effort,
                        is_extreme=is_ext,
                        requires_span_break=False,
                        message=(
                            f"Flecha ajustada para {sag} m"
                            + (" (valor extremo — atenção à altura do cabo)" if is_ext else "")
                            + f". Esforço reduzido de {current_effort:.1f} para {trial_effort:.1f} daN."
                        ),
                        span_suggestions=span_sugs,
                    ))
                    report.solvable_count += 1
                    solved = True
                    break
            if solved:
                break

        if not solved:
            # Nenhuma flecha resolve — necessária quebra de vão
            report.requires_span_break_count += 1
            report.suggestions.append(SolverSuggestion(
                node_id=node.id,
                node_label=node.label,
                current_effort_dan=current_effort,
                target_effort_dan=None,
                is_extreme=False,
                requires_span_break=True,
                message=(
                    f"Esforço de {current_effort:.1f} daN superior a {MAX_STRUCTURAL_DAN:.0f} daN. "
                    "Impossível resolver via flecha. Necessária quebra de vão."
                ),
                span_suggestions=[],
            ))

    return report
