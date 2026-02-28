import math

from .calculators import calculate_level_resultant
from .models import (
    CalculationInput,
    Conductor,
    NodeSpanConfig,
    ProjectNode,
    ProjectTopology,
    TopologyEdge,
    TopologyNode,
)


def build_topology_diagram(
    nodes: list[ProjectNode],
    spans: list[NodeSpanConfig],
    conductors: dict[int, Conductor],
    poles: dict[int, float] # pole_id -> height_m
) -> ProjectTopology:
    """
    Constrói a malha topológica do projeto para o React Flow (Aba 3) e calcula o esforço
    mecânico resultante em cada nó usando a regra de braço de alavanca.
    """
    # 1. Preparar os nós
    topology_nodes = []

    # Mapa para acumular as configurações de vão que atuam em cada nó (chegando ou saindo)
    node_configs_map: dict[int, list[CalculationInput]] = {n.id: [] for n in nodes}
    node_conductors_map: dict[int, list[Conductor]] = {n.id: [] for n in nodes}

    for span in spans:
        # Puxamos os condutores do catálogo
        mt_cond = conductors.get(span.mt_conductor_id)
        bt_cond = conductors.get(span.bt_conductor_id)

        # O vão atua tanto no source quanto no target (com ângulos invertidos ou absolutos dependendo da referência)
        # Para a simplificação do cálculo do esforço no poste, assumimos que o span_length_m empurra o poste.
        # Na vida real a tração = peso * vão^2 / 8 * flecha.

        if mt_cond and mt_cond.id:
            # Source Node MT Input
            if span.source_node_id in node_configs_map:
                node_configs_map[span.source_node_id].append(
                    CalculationInput(
                        span_m=span.span_length_m,
                        sag_m=span.mt_sag_m,
                        angle_deg=span.angle_deg, # Ângulo de saída
                        pole_height_m=poles.get(next((n.pole_id for n in nodes if n.id == span.source_node_id), 0), 9.0),
                        anchorage_height_m=8.5, # Default MT anchor
                        conductor_id=mt_cond.id,
                        level='MT1',
                        level_order=1
                    )
                )
                node_conductors_map[span.source_node_id].append(mt_cond)

            # Target Node MT Input (tração puxando do lado oposto, ângulo + 180)
            if span.target_node_id in node_configs_map:
                node_configs_map[span.target_node_id].append(
                    CalculationInput(
                        span_m=span.span_length_m,
                        sag_m=span.mt_sag_m,
                        angle_deg=(span.angle_deg + 180) % 360,
                        pole_height_m=poles.get(next((n.pole_id for n in nodes if n.id == span.target_node_id), 0), 9.0),
                        anchorage_height_m=8.5,
                        conductor_id=mt_cond.id,
                        level='MT1',
                        level_order=1
                    )
                )
                node_conductors_map[span.target_node_id].append(mt_cond)

        # Repete para BT se existir, alterando as alturas de ancoragem para ~7m
        if bt_cond and bt_cond.id:
            if span.source_node_id in node_configs_map:
                node_configs_map[span.source_node_id].append(
                    CalculationInput(
                        span_m=span.span_length_m,
                        sag_m=span.bt_sag_m,
                        angle_deg=span.angle_deg,
                        pole_height_m=poles.get(next((n.pole_id for n in nodes if n.id == span.source_node_id), 0), 9.0),
                        anchorage_height_m=7.0, # BT Anchor
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
                        pole_height_m=poles.get(next((n.pole_id for n in nodes if n.id == span.target_node_id), 0), 9.0),
                        anchorage_height_m=7.0,
                        conductor_id=bt_cond.id,
                        level='BT',
                        level_order=3
                    )
                )
                node_conductors_map[span.target_node_id].append(bt_cond)

    # 2. Computar Esforço Total por Nó
    for node in nodes:
        inputs = node_configs_map.get(node.id, [])
        conds = node_conductors_map.get(node.id, [])

        total_effort = 0.0
        if inputs and conds:
            # Agrupar por nível porque o braço de alavanca altera o peso no centro de massa do poste
            # MT1
            mt_in = [i for i in inputs if i.level == 'MT1']
            mt_co = [c for i, c in zip(inputs, conds, strict=False) if i.level == 'MT1']
            if mt_in:
                res_mt = calculate_level_resultant(mt_in, mt_co)
                total_effort += res_mt.traction_on_pole_dan

            # BT
            bt_in = [i for i in inputs if i.level == 'BT']
            bt_co = [c for i, c in zip(inputs, conds, strict=False) if i.level == 'BT']
            if bt_in:
                res_bt = calculate_level_resultant(bt_in, bt_co)
                total_effort += res_bt.traction_on_pole_dan

        # Atualiza a entidade em mémoria
        node.effort_dan = round(total_effort, 2)

        topology_nodes.append(TopologyNode(
            id=str(node.id),
            position={"x": node.pos_x, "y": node.pos_y},
            data={"label": node.label, "effort": node.effort_dan}
        ))

    # 3. Preparar Arestas (Edges) com a Regra Estrita de Label (MT cima, BT baixo)
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
    poles: dict[int, float]
) -> list[dict]:
    """
    Retorna uma lista de "Vetores" formatada contendo magnitude, angulo, coord-x, coord-y e cor
    para a renderização exata do Aba 2 (Diagrama de Forças 2.5D), resolvendo a extração do Grafo e trigonometria.
    """
    inputs = []
    conds = []
    node_height = poles.get(node.pole_id, 9.0)

    # Extrair os atuadores do Nó iterando sobre os vãos (Edges)
    for span in spans:
        mt_cond = conductors.get(span.mt_conductor_id)
        bt_cond = conductors.get(span.bt_conductor_id)

        # MT
        if mt_cond and mt_cond.id:
            if span.source_node_id == node.id:
                inputs.append(CalculationInput(span_m=span.span_length_m, sag_m=span.mt_sag_m, angle_deg=span.angle_deg, pole_height_m=node_height, anchorage_height_m=8.5, conductor_id=mt_cond.id, level='MT1', level_order=1))
                conds.append(mt_cond)
            elif span.target_node_id == node.id:
                inputs.append(CalculationInput(span_m=span.span_length_m, sag_m=span.mt_sag_m, angle_deg=(span.angle_deg + 180) % 360, pole_height_m=node_height, anchorage_height_m=8.5, conductor_id=mt_cond.id, level='MT1', level_order=1))
                conds.append(mt_cond)

        # BT
        if bt_cond and bt_cond.id:
            if span.source_node_id == node.id:
                inputs.append(CalculationInput(span_m=span.span_length_m, sag_m=span.bt_sag_m, angle_deg=span.angle_deg, pole_height_m=node_height, anchorage_height_m=7.0, conductor_id=bt_cond.id, level='BT', level_order=3))
                conds.append(bt_cond)
            elif span.target_node_id == node.id:
                inputs.append(CalculationInput(span_m=span.span_length_m, sag_m=span.bt_sag_m, angle_deg=(span.angle_deg + 180) % 360, pole_height_m=node_height, anchorage_height_m=7.0, conductor_id=bt_cond.id, level='BT', level_order=3))
                conds.append(bt_cond)

    vectors = []

    # Vetores Individuais por Tramo
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

    # Vetor Resultante
    if inputs and conds:
        # Pega a resultante e projeta (nesta simplificação assumimos vetor único final pra exibição)
        # Na vida real renderizaríamos um pra MT e um pra BT.
        # Por hora o endpoint atende o Schema Pydantic component_x e component_y
        res = calculate_level_resultant(inputs, conds)
        vectors.append({
            "component_x": res.comp_x,
            "component_y": res.comp_y,
            "magnitude_dan": res.resultant_level_dan,
            "angle_deg": res.resultant_angle_deg,
            "level": "RESULTANTE"
        })

    return vectors
