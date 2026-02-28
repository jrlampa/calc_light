from app.domain.models import Conductor, NodeSpanConfig, ProjectNode
from app.domain.topology_service import build_topology_diagram, calculate_node_force_vectors


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

    poles_dict = {1: 11.0} # Height 11m

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

    assert n1.data["effort"] > 0
    assert n2.data["effort"] > 0
    assert n1.data["effort"] == n2.data["effort"] # symmetric span forces
    assert n1.data["label"] == "Poste 1"

def test_calculate_node_force_vectors():
    node = ProjectNode(id=1, project_id=1, pole_id=1, label="Poste 1", pos_x=0, pos_y=0)
    c1 = Conductor(id=1, name="MT-Cabo", diameter_m=0.015, weight_kg_m=0.6, cable_qty=3, network_type="Conv")
    conductors_dict = {1: c1}
    poles_dict = {1: 11.0}

    span = NodeSpanConfig(
        id=1, source_node_id=1, target_node_id=2,
        mt_conductor_id=1, mt_sag_m=0.5,
        bt_conductor_id=0, bt_sag_m=0.0,
        span_length_m=50, angle_deg=90
    )

    vecs = calculate_node_force_vectors(node, [span], conductors_dict, poles_dict)

    assert len(vecs) == 2 # 1 tramo + 1 resultante
    assert vecs[0]["level"] == "MT1"
    assert vecs[1]["level"] == "RESULTANTE"
    assert vecs[0]["magnitude_dan"] > 0
    assert vecs[1]["magnitude_dan"] > 0
