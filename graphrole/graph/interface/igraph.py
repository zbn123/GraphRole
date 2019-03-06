from functools import partial
from typing import Dict, Iterable, List, Optional, Set

import igraph as ig
import pandas as pd

from graphrole.graph.interface import BaseGraphInterface
from graphrole.types import Edge, Node


class IgraphInterface(BaseGraphInterface):

    """ Interface for igraph Graph object """

    def __init__(self, G: ig.Graph) -> None:
        """
        :param G: igraph Graph
        """
        self.G = G
        self.directed = G.is_directed()

    def get_num_edges(self) -> int:
        """
        Return number of edges in the graph
        """
        return self.G.ecount()

    def get_nodes(self) -> Iterable[Node]:
        """
        Return iterable of nodes in the graph
        """
        return self.G.vs().indices

    def get_neighbors(self, node: Node) -> Iterable[Node]:
        """
        Return iterable of neighbors of specified node
        """
        return self.G.neighbors(node, mode='out')

    def _get_local_features(self) -> pd.DataFrame:
        """
        Return local features for each node in the graph
        """
        if self.directed:
            return pd.DataFrame(
                {
                    'in_degree': self._get_degree_dict(mode='in'),
                    'out_degree': self._get_degree_dict(mode='out'),
                    'total_degree': self._get_degree_dict(),
                }
            )

        return pd.DataFrame.from_dict(
            self._get_degree_dict(),
            orient='index',
            columns=['degree']
        )

    def _get_egonet_features(self) -> pd.DataFrame:
        """
        Return egonet features for each node in the graph
        """
        egonet_features = {}
        for node in self.get_nodes():
            ego_nodes = self.G.neighborhood(node, order=1, mode='out')
            ego = self.G.induced_subgraph(ego_nodes)
            features = {
                'internal_edges': len(ego.es()),
                'external_edges': len(self._get_edge_boundary(ego_nodes))
            }
            egonet_features[node] = features
        return pd.DataFrame.from_dict(egonet_features, orient='index')

    def _get_degree_dict(self, mode: Optional[str] = None) -> Dict[Node, int]:
        """
        Return the mapping of node index to the degree of the node
        :param mode: type of degree ("in", "out", or None for total)
        """
        return {
            vertex.index: vertex.degree(mode=mode)
            for vertex in self.G.vs()
        }

    def _get_edge_boundary(self, interior_vertex_ids: List[Node]) -> List[Edge]:
        """
        Return the list of edges on the boundary of the vertex sets defined
        by interior_vertex_ids and its complement
        :param interior_vertex_ids: list of vertex ids defining the interior
        """
        interior = set(interior_vertex_ids)
        exterior = set(self.get_nodes()) - interior
        _is_boundary = partial(self._is_boundary, interior=interior, exterior=exterior)
        return [edge.tuple for edge in self.G.es() if _is_boundary(edge.tuple)]

    def _is_boundary(self, edge: Edge, interior: Set[Node], exterior: Set[Node]) -> bool:
        """
        Return True if edge is on the boundary of the interior and exterior vertex sets (else False)
        :param edge: edge to evaluate
        :param interior: set of vertex ids
        :param exterior: set of vertex ids
        """
        v1, v2 = edge

        if self.directed:
            return v1 in interior and v2 in exterior

        return (
            (v1 in interior and v2 in exterior)
            or
            (v1 in exterior and v2 in interior)
        )
