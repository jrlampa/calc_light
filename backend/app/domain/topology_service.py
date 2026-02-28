import math

from .calculators import calculate_level_resultant
from .models import (
    CalculationInput,
    Conductor,
    NodeSpanConfig,
    Pole,
    ProjectNode,
    ProjectTopology,
    TopologyEdge,
    TopologyNode,
)


def _pole_height(poles: dict[int, Pole], pole_id: int) -> float:
    pole = poles.get(pole_id)
    return pole.height_m if pole else 9.0


def build_topology_diagram(
    nodes: list[ProjectNode],
    spans: list[NodeSpanConfig],
    conductors: dict[int, Conductor],
    poles: dict[int, Pole]
) -> ProjectTopology:
    """
    Constrói a malha topológica do projeto para o React Flow (Aba 3) e calcula o esforço
    mecânico resultante em cada nó usando a regra de braço de alavanca.
    Inclui utilization_percent, is_overloaded e nominal_capacity no payload do nó.
    """
    topology_nodes = []

    node_configs_map: dict[int, list[CalculationInput]] = {n.id: [] for n in nodes}
    node_conductors_map: dict[int, list[Conductor]] = {n.id: [] for n in nodes}

    for span in spans:
        mt_cond = conductors.get(span.mt_conductor_id)
        bt_cond = conductors.get(span.bt_conductor_id)

        if mt_cond and mt_cond.id:
            if span.source_node_id in node_configs_map:
                node_configs_map[span.source_node_id].append(
                    CalculationInput(
                        span_m=span.span_length_m,
                        sag_m=span.mt_sag_m,
                        angle_deg=span.angle_deg,
                        pole_height_m=_pole_height(poles, next((n.pole_id for n in nodes if n.id == span.source_node_id), 0)),
                        anchorage_height_m=8.5,
                        conductor_id=mt_cond.id,
                        level='MT1',
                        level_order=1
                    )
                )
                node_conductors_map[span.source_node_id].append(mt_cond)

            if span.target_node_id in node_configs_map:
                node_configs_map[span.target_node_id].append(
                    CalculationInput(
                        span_m=span.span_length_m,
                        sag_m=span.mt_sag_m,
                        angle_deg=(span.angle_deg + 180) % 360,
                        pole_height_m=_pole_height(poles, next((n.pole_id for n in nodes if n.id == span.target_node_id), 0)),
                        anchorage_height_m=8.5,
                        conductor_id=mt_cond.id,
                        level='MT1',
                        level_order=1
                    )
                )
                node_conductors_map[span.target_node_id].append(mt_cond)

        if bt_cond and bt_cond.id:
            if span.source_node_id in node_configs_map:
                node_configs_map[span.source_node_id].append(
                    CalculationInput(
                        span_m=span.span_length_m,
                        sag_m=span.bt_sag_m,
                        angle_deg=span.angle_deg,
                        pole_height_m=_pole_height(poles, next((n.pole_id for n in nodes if n.id == span.source_node_id), 0)),
                        anchorage_height_m=7.0,
                        conductor_id=bt_cond.id,
                        level='BT',
                        level_order=3
                    )
                )
                node_conductors_map[span.source_node_id].append(bt_cond)

            if span.target_node_id in node_configs_map:
                node_configs_map[span.target_node_id].append(
                    CalculationInput(
                        span_m=span.span_length_m,
                        sag_m=span.bt_sag_m,
                        angle_deg=(span.angle_deg + 180) % 360,
                        pole_height_m=_pole_height(poles, next((n.pole_id for n in nodes if n.id == span.target_node_id), 0)),
                        anchorage_height_m=7.0,
                        conductor_id=bt_cond.id,
                        level='BT',
                        level_order=3
                    )
                )
                node_conductors_map[span.target_node_id].append(bt_cond)

    # Computar Esforço Total por Nó + Margem de Segurança
    for node in nodes:
        inputs = node_configs_map.get(node.id, [])
        conds = node_conductors_map.get(node.id, [])

        total_effort = 0.0
        if inputs and conds:
            mt_in = [i for i in inputs if i.level == 'MT1']
            mt_co = [c for i, c in zip(inputs, conds, strict=False) if i.level == 'MT1']
            if mt_in:
                res_mt = calculate_level_resultant(mt_in, mt_co)
                total_effort += res_mt.traction_on_pole_dan

            bt_in = [i for i in inputs if i.level == 'BT']
            bt_co = [c for i, c in zip(inputs, conds, strict=False) if i.level == 'BT']
            if bt_in:
                res_bt = calculate_level_resultant(bt_in, bt_co)
                total_effort += res_bt.traction_on_pole_dan

        node.effort_dan = round(total_effort, 2)

        # Margem de segurança baseada na resistência nominal do catálogo
        pole_obj = poles.get(node.pole_id)
        nominal_capacity = pole_obj.resistance_dan if pole_obj and pole_obj.resistance_dan > 0 else 0.0
        utilization_percent = round((node.effort_dan / nominal_capacity) * 100, 1) if nominal_capacity > 0 else 0.0
        is_overloaded = utilization_percent > 100.0

        topology_nodes.append(TopologyNode(
            id=str(node.id),
            position={"x": node.pos_x, "y": node.pos_y},
            data={
                "label": node.label,
                "effort_dan": node.effort_dan,
                "utilization_percent": utilization_percent,
                "is_overloaded": is_overloaded,
                "nominal_capacity": nominal_capacity,
            }
        ))

    # Preparar Arestas (Edges) com a Regra Estrita de Label (MT cima, BT baixo)
    topology_edges = []
    for span in spans:
        mt_c = conductors.get(span.mt_conductor_id)
        bt_c = conductors.get(span.bt_conductor_id)

        mt_label = f"{mt_c.name} (Fl: {span.mt_sag_m}m)" if mt_c else ""
        bt_label = f"{bt_c.name} (Fl: {span.bt_sag_m}m)" if bt_c else ""

        topology_edges.append(TopologyEdge(
            id=f"e-{span.source_node_id}-{span.target_node_id}",
            source=str(span.source_node_id),
            target=str(span.target_node_id),
            mt_label=mt_label,
            bt_label=bt_label
        ))

    return ProjectTopology(nodes=topology_nodes, edges=topology_edges)


def calculate_node_force_vectors(
    node: ProjectNode,
    spans: list[NodeSpanConfig],
    conductors: dict[int, Conductor],
    poles: dict[int, Pole]
) -> list[dict]:
    """
    Retorna uma lista de Vetores para o Diagrama de Forças (Aba 2).
    Inclui nominal_capacity no vetor RESULT para plotar o Círculo de Limite.
    """
    inputs = []
    conds = []
    node_height = _pole_height(poles, node.pole_id)

    for span in spans:
        mt_cond = conductors.get(span.mt_conductor_id)
        bt_cond = conductors.get(span.bt_conductor_id)

        if mt_cond and mt_cond.id:
            if span.source_node_id == node.id:
                inputs.append(CalculationInput(span_m=span.span_length_m, sag_m=span.mt_sag_m, angle_deg=span.angle_deg, pole_height_m=node_height, anchorage_height_m=8.5, conductor_id=mt_cond.id, level='MT1', level_order=1))
                conds.append(mt_cond)
            elif span.target_node_id == node.id:
                inputs.append(CalculationInput(span_m=span.span_length_m, sag_m=span.mt_sag_m, angle_deg=(span.angle_deg + 180) % 360, pole_height_m=node_height, anchorage_height_m=8.5, conductor_id=mt_cond.id, level='MT1', level_order=1))
                conds.append(mt_cond)

        if bt_cond and bt_cond.id:
            if span.source_node_id == node.id:
                inputs.append(CalculationInput(span_m=span.span_length_m, sag_m=span.bt_sag_m, angle_deg=span.angle_deg, pole_height_m=node_height, anchorage_height_m=7.0, conductor_id=bt_cond.id, level='BT', level_order=3))
                conds.append(bt_cond)
            elif span.target_node_id == node.id:
                inputs.append(CalculationInput(span_m=span.span_length_m, sag_m=span.bt_sag_m, angle_deg=(span.angle_deg + 180) % 360, pole_height_m=node_height, anchorage_height_m=7.0, conductor_id=bt_cond.id, level='BT', level_order=3))
                conds.append(bt_cond)

    vectors = []

    for calc_input, conductor in zip(inputs, conds, strict=False):
        total_weight = conductor.weight_kg_m * conductor.cable_qty + conductor.messenger_weight
        traction = (total_weight * calc_input.span_m**2) / (8 * calc_input.sag_m) if calc_input.sag_m > 0 else 0.0

        comp_x = round(traction * math.cos(math.radians(calc_input.angle_deg)), 2)
        comp_y = round(traction * math.sin(math.radians(calc_input.angle_deg)), 2)

        vectors.append({
            "component_x": comp_x,
            "component_y": comp_y,
            "magnitude_dan": round(traction, 2),
            "angle_deg": calc_input.angle_deg,
            "level": calc_input.level
        })

    if inputs and conds:
        pole_obj = poles.get(node.pole_id)
        nominal_capacity = pole_obj.resistance_dan if pole_obj and pole_obj.resistance_dan > 0 else 0.0

        res = calculate_level_resultant(inputs, conds)
        vectors.append({
            "component_x": res.comp_x,
            "component_y": res.comp_y,
            "magnitude_dan": res.resultant_level_dan,
            "angle_deg": res.resultant_angle_deg,
            "level": "RESULT",
            "nominal_capacity": nominal_capacity,
        })

    return vectors
