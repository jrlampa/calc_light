import networkx as nx
from typing import Dict, List, Tuple
from .electrical_models import (
    GraphPayloadSchema, GraphNodeSchema, GraphEdgeSchema, 
    CqtInputSchema, PosteSchema, RamalSchema
)

class TopologyError(Exception):
    """Lançado para erros de topologia de rede (ex: anéis, múltiplos trafos)."""
    pass

class TopologyParser:
    def __init__(self):
        pass

    def parse_to_cqt_input(self, payload: GraphPayloadSchema) -> CqtInputSchema:
        """
        Converte o payload de Grafo (React Flow) para a estrutura linear do Motor CQT.
        Valida integridade, radialidade e gera ordenação topológica.
        """
        # 1. Construir o Grafo
        G = nx.DiGraph()
        nodes_data: Dict[str, GraphNodeSchema] = {n.id: n for n in payload.nodes}
        
        for n in payload.nodes:
            G.add_node(n.id)
            
        for e in payload.edges:
            if e.source not in nodes_data or e.target not in nodes_data:
                continue
            G.add_edge(e.source, e.target, 
                       id=e.id, 
                       condutor=e.condutor, 
                       comprimento=e.comprimento, 
                       fases=e.fases, 
                       tipo_trecho=e.tipo_trecho)

        # 2. Identificar Raiz (Transformer)
        transformers = [n for n in payload.nodes if n.is_transformer]
        if len(transformers) == 0:
            raise TopologyError("A rede deve conter exatamente um transformador (is_transformer=True).")
        if len(transformers) > 1:
            raise TopologyError("Múltiplos transformadores detectados na mesma rede BT.")
            
        root_id = transformers[0].id

        # 3. Validar Radialidade (Anti-Anel)
        if not nx.is_directed_acyclic_graph(G):
            raise TopologyError("Rede em anel detectada. A topologia BT da Light deve ser estritamente radial (DAG).")

        # 4. Bifurcação automática: Lado 1 e Lado 2
        # Pegamos as arestas saindo da raiz
        out_edges = list(G.out_edges(root_id))
        
        lado_1_nodes = []
        lado_2_nodes = []
        
        # Se houver apenas uma saída, envia tudo pro Lado 1
        # Se houver duas, separa. Se houver mais, as demais vão pro Lado 1 ou 2 sequencialmente.
        lado_1_postes = []
        lado_2_postes = []

        for idx, (u, v) in enumerate(out_edges):
            # Encontrar subgrafo descendo por v
            reachable = nx.descendants(G, v) | {v}
            sub_G = G.subgraph(reachable).copy()
            
            # Ordenar topologicamente
            sorted_nodes = list(nx.topological_sort(sub_G))
            
            # Converter arestas desse subgrafo em PosteSchema
            side_postes = self._build_path_postes(G, sorted_nodes, nodes_data)
            
            if idx == 0:
                lado_1_postes.extend(side_postes)
            else:
                lado_2_postes.extend(side_postes)

        return CqtInputSchema(
            u_nominal=payload.u_nominal,
            leitura_trafo=payload.leitura_trafo,
            trafo_nominal_kva=payload.trafo_nominal_kva,
            lado_1=lado_1_postes,
            lado_2=lado_2_postes
        )

    def _build_path_postes(self, G: nx.DiGraph, sorted_nodes: List[str], nodes_data: Dict[str, GraphNodeSchema]) -> List[PosteSchema]:
        """Auxiliar para converter nós ordenados em trechos (PosteSchema)."""
        postes = []
        for node_id in sorted_nodes:
            # Para cada nó no caminho ordenado, precisamos da aresta que chega nele (in_edge)
            # Exceto se houver bifurcação, o nó pode ter apenas 1 pai no DAG radial
            in_edges = list(G.in_edges(node_id, data=True))
            
            if not in_edges:
                continue # Nó raiz do subgrafo (primeiro após o trafo) processamos arestas dele
                
            # Como é radial, esperamos apenas 1 in_edge
            parent, child, data = in_edges[0]
            
            node_info = nodes_data[node_id]
            
            postes.append(PosteSchema(
                id=node_id,
                condutor=data['condutor'],
                comprimento=data['comprimento'],
                fases=data['fases'],
                ramais=node_info.ramais,
                tipo_trecho=data['tipo_trecho']
            ))
            
        return postes
