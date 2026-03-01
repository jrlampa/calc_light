from app.domain.models import Conductor, NodeSpanConfig, Pole, ProjectNode
from app.domain.topology_service import build_topology_diagram, calculate_node_force_vectors


def _make_pole(height_m: float = 11.0, resistance_dan: float = 600.0) -> Pole:
    return Pole(id=1, type_name="Poste Teste", height_m=height_m, resistance_dan=resistance_dan)


def test_build_topology_diagram_isolated():
    # Arrange Mock Data
    nodes = [
        ProjectNode(id=1, project_id=1, pole_id=1, label="Poste 1", pos_x=0, pos_y=0),
        ProjectNode(id=2, project_id=1, pole_id=1, label="Poste 2", pos_x=100, pos_y=0)
    ]

    c1 = Conductor(id=1, name="MT-Cabo1", diameter_m=0.015, weight_kg_m=0.6, cable_qty=3, network_type="Conv")
    c2 = Conductor(id=2, name="BT-Cabo2", diameter_m=0.010, weight_kg_m=0.3, cable_qty=4, network_type="Conv")
    conductors_dict = {1: c1, 2: c2}

    spans = [
        NodeSpanConfig(
            id=1, source_node_id=1, target_node_id=2,
            mt_conductor_id=1, mt_sag_m=0.5,
            bt_conductor_id=2, bt_sag_m=0.6,
            span_length_m=50, angle_deg=90
        )
    ]

    poles_dict = {1: _make_pole(height_m=11.0, resistance_dan=600.0)}

    # Act
    topo = build_topology_diagram(nodes, spans, conductors_dict, poles_dict)

    # Assert
    assert len(topo.nodes) == 2
    assert len(topo.edges) == 1

    # Verificar Labels do React Flow
    edge = topo.edges[0]
    assert "MT-Cabo1" in edge.mt_label
    assert "BT-Cabo2" in edge.bt_label

    # Verificar Esforço Calculado
    n1 = [n for n in topo.nodes if n.id == "1"][0]
    n2 = [n for n in topo.nodes if n.id == "2"][0]

    assert n1.data["effort_dan"] > 0
    assert n2.data["effort_dan"] > 0
    assert n1.data["effort_dan"] == n2.data["effort_dan"]  # symmetric span forces
    assert n1.data["label"] == "Poste 1"


def test_utilization_percent_and_overload_flag():
    """Garante que utilization_percent e is_overloaded são calculados corretamente."""
    nodes = [
        ProjectNode(id=1, project_id=1, pole_id=1, label="Seguro", pos_x=0, pos_y=0),
        ProjectNode(id=2, project_id=1, pole_id=2, label="Sobrecarregado", pos_x=100, pos_y=0),
    ]

    c1 = Conductor(id=1, name="MT-Cabo1", diameter_m=0.015, weight_kg_m=0.6, cable_qty=3, network_type="Conv")
    conductors_dict = {1: c1}

    spans = [
        NodeSpanConfig(
            id=1, source_node_id=1, target_node_id=2,
            mt_conductor_id=1, mt_sag_m=0.5,
            bt_conductor_id=None, bt_sag_m=0.0,
            span_length_m=50, angle_deg=90
        )
    ]

    # Poste 1: alta resistência → não sobrecarregado
    # Poste 2: resistência muito baixa → sobrecarregado
    poles_dict = {
        1: Pole(id=1, type_name="Alto", height_m=11.0, resistance_dan=9999.0),
        2: Pole(id=2, type_name="Fraco", height_m=11.0, resistance_dan=1.0),
    }

    topo = build_topology_diagram(nodes, spans, conductors_dict, poles_dict)

    n_safe = next(n for n in topo.nodes if n.id == "1")
    n_over = next(n for n in topo.nodes if n.id == "2")

    # Nó seguro: utilização < 100%
    assert n_safe.data["utilization_percent"] < 100.0
    assert n_safe.data["is_overloaded"] is False

    # Nó sobrecarregado: utilização > 100%
    assert n_over.data["utilization_percent"] > 100.0
    assert n_over.data["is_overloaded"] is True

    # nominal_capacity deve estar presente
    assert n_safe.data["nominal_capacity"] == 9999.0
    assert n_over.data["nominal_capacity"] == 1.0


def test_calculate_node_force_vectors():
    node = ProjectNode(id=1, project_id=1, pole_id=1, label="Poste 1", pos_x=0, pos_y=0)
    c_mt = Conductor(id=1, name="MT-Cabo", diameter_m=0.015, weight_kg_m=0.6, cable_qty=3, network_type="Conv")
    c_bt = Conductor(id=2, name="BT-Cabo", diameter_m=0.010, weight_kg_m=0.3, cable_qty=4, network_type="Conv")
    conductors_dict = {1: c_mt, 2: c_bt}
    poles_dict = {1: _make_pole(height_m=11.0, resistance_dan=600.0)}

    span = NodeSpanConfig(
        id=1, source_node_id=1, target_node_id=2,
        mt_conductor_id=1, mt_sag_m=0.5,
        bt_conductor_id=2, bt_sag_m=0.6,
        span_length_m=50, angle_deg=90
    )

    vecs = calculate_node_force_vectors(node, [span], conductors_dict, poles_dict)

    # MT1 + BT + RESULT
    assert len(vecs) == 3
    levels = {v["level"] for v in vecs}
    assert "MT1" in levels
    assert "BT" in levels
    assert "RESULT" in levels

    result_vec = next(v for v in vecs if v["level"] == "RESULT")
    assert result_vec["magnitude_dan"] > 0
    assert "nominal_capacity" in result_vec
    assert result_vec["nominal_capacity"] == 600.0


def test_calculate_node_force_vectors_as_target():
    """Cobre o caminho target_node_id == node.id (linhas 214-216, 219-224 de topology_service.py)."""
    # Nó 2 é o TARGET do vão (não a fonte)
    node = ProjectNode(id=2, project_id=1, pole_id=1, label="Poste 2", pos_x=100, pos_y=0)
    c_mt = Conductor(id=1, name="MT-Cabo", diameter_m=0.015, weight_kg_m=0.6, cable_qty=3, network_type="Conv")
    c_bt = Conductor(id=2, name="BT-Cabo", diameter_m=0.010, weight_kg_m=0.3, cable_qty=4, network_type="Conv")
    conductors_dict = {1: c_mt, 2: c_bt}
    poles_dict = {1: _make_pole(height_m=11.0, resistance_dan=600.0)}

    span = NodeSpanConfig(
        id=1, source_node_id=1, target_node_id=2,
        mt_conductor_id=1, mt_sag_m=0.5,
        bt_conductor_id=2, bt_sag_m=0.6,
        span_length_m=50, angle_deg=45
    )

    vecs = calculate_node_force_vectors(node, [span], conductors_dict, poles_dict)

    # Deve ter MT1 + BT + RESULT
    assert len(vecs) == 3
    levels = {v["level"] for v in vecs}
    assert "MT1" in levels
    assert "BT" in levels
    assert "RESULT" in levels

    # O ângulo do vão deve ser invertido (+ 180°) para o nó alvo
    mt_vec = next(v for v in vecs if v["level"] == "MT1")
    expected_angle = (45 + 180) % 360
    assert mt_vec["angle_deg"] == expected_angle


def test_calculate_node_force_vectors_no_spans():
    """Sem vãos conectados, retorna lista vazia (sem vetor RESULT)."""
    node = ProjectNode(id=1, project_id=1, pole_id=1, label="Poste 1", pos_x=0, pos_y=0)
    poles_dict = {1: _make_pole()}
    vecs = calculate_node_force_vectors(node, [], {}, poles_dict)
    assert vecs == []
