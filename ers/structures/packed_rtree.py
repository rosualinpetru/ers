"""
Packed (bulk-loaded) R-trees over minimum bounding hyperrectangles.

An R-tree (Guttman, SIGMOD 1984) stores points in bounded leaves and groups
leaves into internal nodes, each carrying the minimum bounding box (MBR) of its
subtree. *Packing* builds the tree bottom-up from a sorted order of the points
instead of by dynamic insertion, which produces full nodes with little overlap.
Two packing orders are implemented on top of the shared :class:`PackedRTree`:

* :class:`~ers.structures.hilbert_rtree.HilbertRTree` sorts points along a
  Hilbert curve (Kamel & Faloutsos, VLDB 1994);
* :class:`~ers.structures.str_rtree.STRRTree` tiles them axis by axis
  (Sort-Tile-Recursive, Leutenegger et al., ICDE 1997).

Both share the node type, the level-packing loop and the cover algorithm, so
comparing them isolates exactly what the packing order contributes.

Because its shape follows the data, a packed R-tree is inherently
**data-dependent**: the client keeps the tree (or the points to rebuild it)
and refers to nodes by deterministic ids, which reveal nothing to the server.
"""

from itertools import count
from typing import Iterator, List, Optional

from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point


class RTreeNode:
    """
    A node of a packed R-tree: a bounding box plus either child nodes
    (internal node) or data points (leaf). Nodes carry a deterministic
    :attr:`node_id` assigned in construction order, so a client that rebuilds
    the same tree can label index entries by id alone.
    """

    def __init__(self, node_id: int, bbox: HyperRange, children: Optional[List["RTreeNode"]] = None, points: Optional[List[Point]] = None):
        """
        :param node_id: Deterministic identifier of the node.
        :param bbox: Minimum bounding hyperrectangle of the subtree.
        :param children: Child nodes (internal node) or ``None``.
        :param points: Data points (leaf) or ``None``.
        """
        self.node_id = node_id
        self.bbox = bbox
        self.children = children or []
        self.points = points or []

    @property
    def is_leaf(self) -> bool:
        """Whether the node holds points rather than child nodes."""
        return not self.children

    def subtree_points(self) -> List[Point]:
        """All data points stored beneath this node."""
        if self.is_leaf:
            return list(self.points)
        pts: List[Point] = []
        for c in self.children:
            pts.extend(c.subtree_points())
        return pts


class PackedRTree:
    """
    A bulk-loaded R-tree. Subclasses decide the order in which points are
    chunked into leaves; everything else -- packing the levels, covering a
    query, enumerating the nodes -- is shared.
    """

    def __init__(self, root: Optional[RTreeNode], node_capacity: int):
        """
        :param root: The root node, or ``None`` for an empty tree.
        :param node_capacity: Maximum fan-out of internal nodes and size of leaves.
        """
        self.root = root
        self.node_capacity = node_capacity

    # ------------------------------------------------------------------ #
    # Construction.
    # ------------------------------------------------------------------ #
    @classmethod
    def _pack(cls, leaf_chunks: List[List[Point]], node_capacity: int) -> Optional[RTreeNode]:
        """
        Packs leaf chunks into leaves and the leaves into successive internal
        levels, ``node_capacity`` nodes at a time, until a single root remains.

        :param leaf_chunks: The points of each leaf, in packing order.
        :param node_capacity: Maximum fan-out / leaf size.
        :return: The root, or ``None`` if there are no points.
        """
        if not leaf_chunks:
            return None

        ids = count()
        level = [RTreeNode(next(ids), cls._bounding_box_of_points(chunk), points=chunk) for chunk in leaf_chunks]
        while len(level) > 1:
            parents: List[RTreeNode] = []
            for i in range(0, len(level), node_capacity):
                chunk = level[i : i + node_capacity]
                parents.append(RTreeNode(next(ids), cls._bounding_box_of_ranges([c.bbox for c in chunk]), children=chunk))
            level = parents
        return level[0]

    # ------------------------------------------------------------------ #
    # Query: a cover of R-tree nodes whose union contains every query point.
    # ------------------------------------------------------------------ #
    def cover(self, query: HyperRange) -> List[RTreeNode]:
        """
        Returns nodes whose subtrees together contain **every** data point in
        ``query`` (no false negatives).

        Descent rule: skip a node whose box misses the query; take a node whose
        box lies fully inside the query (all its points match); for a node that
        only partially overlaps, recurse into its children, or, if it is a leaf,
        take it whole and let the client filter out the few points outside the
        query. Partially overlapping leaves are the only source of false positives.

        :param query: The range to cover.
        :return: The covering nodes.
        """
        result: List[RTreeNode] = []
        stack = [self.root] if self.root is not None else []
        while stack:
            node = stack.pop()
            if not node.bbox.intersects(query):
                continue
            if node.bbox in query or node.is_leaf:
                result.append(node)
            else:
                stack.extend(node.children)
        return result

    def all_nodes(self) -> List[RTreeNode]:
        """Every node of the tree, in pre-order (used to build the encrypted index)."""
        return list(self._iter_nodes())

    def _iter_nodes(self) -> Iterator[RTreeNode]:
        stack = [self.root] if self.root is not None else []
        while stack:
            node = stack.pop()
            yield node
            stack.extend(node.children)

    # ------------------------------------------------------------------ #
    # Helpers.
    # ------------------------------------------------------------------ #
    @staticmethod
    def _bounding_box_of_points(points: List[Point]) -> HyperRange:
        """The minimum bounding box of a non-empty list of points."""
        d = points[0].dimensions()
        return HyperRange.from_coords([min(p[i] for p in points) for i in range(d)], [max(p[i] for p in points) for i in range(d)])

    @staticmethod
    def _bounding_box_of_ranges(ranges: List[HyperRange]) -> HyperRange:
        """The minimum bounding box of a non-empty list of ranges."""
        d = ranges[0].dimensions
        return HyperRange.from_coords([min(r.start[i] for r in ranges) for i in range(d)], [max(r.end[i] for r in ranges) for i in range(d)])
