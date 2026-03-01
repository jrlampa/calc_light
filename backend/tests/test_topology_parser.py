import pytest
from app.domain.topology_parser import TopologyParser, TopologyError
from app.domain.electrical_models import GraphPayloadSchema, GraphNodeSchema, GraphEdgeSchema, RamalSchema

@pytest.fixture
def parser():
    return TopologyParser()

def test_straight_line_topology(parser):
    # Trafo (R) -> P1 -> P2
    payload = GraphPayloadSchema(
        nodes=[
            GraphNodeSchema(id="R", is_transformer=True),
            GraphNodeSchema(id="P1", ramais=[RamalSchema(tipo="33", qtd=1)]),
            GraphNodeSchema(id="P2", ramais=[RamalSchema(tipo="33", qtd=2)])
        ],
        edges=[
            GraphEdgeSchema(id="e1", source="R", target="P1", condutor="240 Cu", comprimento=10, fases=3),
            GraphEdgeSchema(id="e2", source="P1", target="P2", condutor="70 Al", comprimento=20, fases=3)
        ]
    )
    res = parser.parse_to_cqt_input(payload)
    assert len(res.lado_1) == 2
    assert res.lado_1[0].id == "P1"
    assert res.lado_1[1].id == "P2"
    assert res.lado_1[1].condutor == "70 Al"

def test_bifurcation_topology(parser):
    # P1 <- Trafo (R) -> P2
    payload = GraphPayloadSchema(
        nodes=[
            GraphNodeSchema(id="R", is_transformer=True),
            GraphNodeSchema(id="P1"),
            GraphNodeSchema(id="P2")
        ],
        edges=[
            GraphEdgeSchema(id="e1", source="R", target="P1", condutor="240 Cu", comprimento=10, fases=3),
            GraphEdgeSchema(id="e2", source="R", target="P2", condutor="240 Cu", comprimento=10, fases=3)
        ]
    )
    res = parser.parse_to_cqt_input(payload)
    assert len(res.lado_1) == 1
    assert len(res.lado_2) == 1
    assert res.lado_1[0].id == "P1"
    assert res.lado_2[0].id == "P2"

def test_missing_transformer(parser):
    payload = GraphPayloadSchema(
        nodes=[GraphNodeSchema(id="P1")],
        edges=[]
    )
    with pytest.raises(TopologyError, match="exatamente um transformador"):
        parser.parse_to_cqt_input(payload)

def test_multiple_transformers(parser):
    payload = GraphPayloadSchema(
        nodes=[
            GraphNodeSchema(id="R1", is_transformer=True),
            GraphNodeSchema(id="R2", is_transformer=True)
        ],
        edges=[]
    )
    with pytest.raises(TopologyError, match="Múltiplos transformadores"):
        parser.parse_to_cqt_input(payload)

def test_cycle_detection(parser):
    # R -> P1 -> P2 -> P1 (Loop)
    payload = GraphPayloadSchema(
        nodes=[
            GraphNodeSchema(id="R", is_transformer=True),
            GraphNodeSchema(id="P1"),
            GraphNodeSchema(id="P2")
        ],
        edges=[
            GraphEdgeSchema(id="e1", source="R", target="P1", condutor="33", comprimento=10, fases=3),
            GraphEdgeSchema(id="e2", source="P1", target="P2", condutor="33", comprimento=10, fases=3),
            GraphEdgeSchema(id="e3", source="P2", target="P1", condutor="33", comprimento=10, fases=3)
        ]
    )
    with pytest.raises(TopologyError, match="Rede em anel detectada"):
        parser.parse_to_cqt_input(payload)

def test_isolated_nodes_ignored(parser):
    # R -> P1, P99 (Isolated)
    payload = GraphPayloadSchema(
        nodes=[
            GraphNodeSchema(id="R", is_transformer=True),
            GraphNodeSchema(id="P1"),
            GraphNodeSchema(id="P99")
        ],
        edges=[
            GraphEdgeSchema(id="e1", source="R", target="P1", condutor="33", comprimento=10, fases=3)
        ]
    )
    res = parser.parse_to_cqt_input(payload)
    assert len(res.lado_1) == 1
    ids = [p.id for p in res.lado_1]
    assert "P99" not in ids

def test_invalid_edge_references_ignored(parser):
    # R -> P1, edge to P_NONEXIST
    payload = GraphPayloadSchema(
        nodes=[
            GraphNodeSchema(id="R", is_transformer=True),
            GraphNodeSchema(id="P1")
        ],
        edges=[
            GraphEdgeSchema(id="e1", source="R", target="P1", condutor="33", comprimento=10, fases=3),
            GraphEdgeSchema(id="e2", source="P1", target="P_GHOST", condutor="33", comprimento=10, fases=3)
        ]
    )
    res = parser.parse_to_cqt_input(payload)
    assert len(res.lado_1) == 1

def test_internal_build_path_postes_guard(parser):
    # Testar o guard de nó sem pai diretamente
    import networkx as nx
    G = nx.DiGraph()
    G.add_node("ROOT")
    postes = parser._build_path_postes(G, ["ROOT"], {"ROOT": GraphNodeSchema(id="ROOT")})
    assert len(postes) == 0
