"""
Range-search schemes over a packed R-tree.

Each record is stored under the label of every ancestor node of its point, so
one token per node of :meth:`PackedRTree.cover` retrieves the node's whole
subtree. Nodes are labelled by their deterministic id: the client rebuilds the
identical tree locally and refers to nodes by id, so the server never learns a
bounding box. The scheme is **data-dependent** (the tree shape is client state
that follows the data) and lossy only through partially overlapping boundary
leaves.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Set

from tqdm import tqdm

from ers.schemes.common.emm import EMM
from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.hyperrange import HyperRange
from ers.structures.packed_rtree import PackedRTree
from ers.structures.point import Point
from ers.util.serialization.serialization import ObjectToBytes


class PackedRTreeScheme(EMM):
    """A range-search scheme whose range-supporting structure is a packed R-tree."""

    exact = False

    def __init__(self, emm_engine: EMMEngine, node_capacity: int = 4):
        """
        :param emm_engine: The engine providing the cryptographic primitives.
        :param node_capacity: Maximum R-tree fan-out / leaf size.
        """
        super().__init__(emm_engine)
        self.node_capacity = node_capacity
        #: The client-held tree, built by :meth:`build_index`.
        self.tree: Optional[PackedRTree] = None

    def _build_tree(self, points: List[Point]) -> PackedRTree:
        """Bulk-loads the tree over the data points (the packing order is the subclass's choice)."""
        raise NotImplementedError

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]) -> None:
        """
        Bulk-loads the tree and encrypts one postings list per node.

        :param key: The secret key used to encrypt the index.
        :param plaintext_mm: A mapping from data points to their records.
        """
        for point in plaintext_mm:
            assert point.dimensions() == self.dimensions
        self.tree = self._build_tree(list(plaintext_mm.keys()))

        modified_db: Dict[bytes, List[bytes]] = defaultdict(list)
        for node in tqdm(self.tree.all_nodes()):
            label = self._node_label(node.node_id)
            for p in node.subtree_points():
                modified_db[label].extend(plaintext_mm[p])

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRange) -> Set[bytes]:
        """
        Generates one token per node in the R-tree cover of the query.

        :param key: The secret key used to derive the tokens.
        :param query: The range to search.
        :return: The set of search tokens.
        :raises ValueError: If the index has not been built yet.
        """
        assert query.dimensions == self.dimensions
        if self.tree is None:
            raise ValueError("Index is not built yet!")
        return {self.emm_engine.trapdoor(key, self._node_label(node.node_id)) for node in self.tree.cover(query)}

    @staticmethod
    def _node_label(node_id: int) -> bytes:
        """The index label of a node: its id, never its bounding box."""
        return ObjectToBytes(["rtree_node", node_id])
