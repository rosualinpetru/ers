"""
Native multi-dimensional interactive double-index scheme.

:class:`InteractiveSRCNative` runs the two-round ``Logarithmic-SRC-i`` protocol
(:class:`InteractiveSRC`) directly on the **native multi-dimensional grid**,
without a Hilbert linearisation. It fills the "interactive × native" cell of
the design space and is the natural head-to-head baseline for
:class:`InteractiveSRCHilbert`.

How the two variants differ
---------------------------
The protocol needs (a) an integer *value* per record that orders the documents,
(b) a round-one structure over the value domain answering a single-node SRC
cover, and (c) a client-side test of whether a value truly matches a query.

* **Hilbert variant**: value = Hilbert distance; round one is a 1-D TDAG over
  the Hilbert domain; the client decodes each leaf back to its grid point.
* **Native variant (this class)**: value = the point's **lexicographic
  (row-major) rank**; round one is a **product of per-dimension TDAGs** — the
  same structure :class:`TdagSRC` queries — so its single token is the product
  SRC node of the query rectangle itself. The client decodes a rank back to
  its grid point with plain mixed-radix arithmetic.

Trade-off intuition
-------------------
Round one is equally cheap in both variants (one token). The difference shows
in round two: after filtering, the surviving document indices form runs that
are contiguous *along the chosen linearisation*. Lexicographic order makes one
run per "row" of the query rectangle, so the number of round-two tokens grows
with the query's extent in the leading dimensions, whereas Hilbert order tends
to produce fewer, longer runs. In exchange, the native variant needs no curve
machinery and its round-one cover is exactly the TdagSRC product node, making
the comparison against non-interactive TdagSRC completely like-for-like.
"""

from typing import List, Optional

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.interactive.interactive_src import InteractiveSRC
from ers.structures.hyperrange import HyperRange
from ers.structures.hyperrange_tree import HyperRangeTree
from ers.structures.hyperrange_tree_product import HyperRangeTreeProduct
from ers.structures.point import Point
from ers.util.hyperrange.uniform_split_mid_overlap_divider import UniformSplitMidOverlapDivider


class InteractiveSRCNative(InteractiveSRC):
    """
    The interactive double-index scheme over the native multi-dimensional
    domain, using lexicographic document order and a product-TDAG round one.
    """

    def __init__(self, emm_engine: EMMEngine, single_range_cover_round2: bool = True):
        """
        :param emm_engine: The EMM engine providing the cryptographic primitives.
        :param single_range_cover_round2: If ``True`` the second round uses SRC
            (one token per surviving interval, may overshoot); if ``False`` it
            uses BRC (more tokens, precision 1).
        """
        super().__init__(emm_engine, single_range_cover_round2)
        # Per-dimension domain sizes, used for the mixed-radix rank encoding.
        self._dim_sizes = [2**b for b in emm_engine.DIMENSIONS_BITS]

    # ------------------------------------------------------------------ #
    # Value domain: lexicographic (row-major) rank of the grid point.
    # ------------------------------------------------------------------ #
    def _value_of(self, point: Point) -> int:
        """Mixed-radix (row-major) rank of ``point``; orders the documents."""
        assert point.dimensions() == len(self._dim_sizes)
        rank = 0
        for i, size in enumerate(self._dim_sizes):
            rank = rank * size + point[i]
        return rank

    def _point_of(self, rank: int) -> Point:
        """Inverse of :meth:`_value_of`: decode a rank back to its grid point."""
        coords: List[int] = []
        for size in reversed(self._dim_sizes):
            coords.append(rank % size)
            rank //= size
        return Point(coords[::-1])

    # ------------------------------------------------------------------ #
    # Round-one structure: the TdagSRC product of per-dimension TDAGs.
    # ------------------------------------------------------------------ #
    def _build_value_tdag(self) -> "HyperRangeTreeProduct":
        """One uniform mid-overlap TDAG per dimension, combined as a product."""
        return HyperRangeTreeProduct(
            [HyperRangeTree.init(HyperRange.from_bits([b]), UniformSplitMidOverlapDivider(2)) for b in self.emm_engine.DIMENSIONS_BITS]
        )

    def _descend_value(self, v: int) -> List[HyperRange]:
        """All product nodes covering the grid point encoded by rank ``v``."""
        return self.tdag_val.descend(HyperRange.from_point(self._point_of(v)))

    def _round1_cover_node(self, query: HyperRange) -> Optional[HyperRange]:
        """The single product node covering the query rectangle directly."""
        assert query.dimensions == len(self._dim_sizes)
        return self.tdag_val.src(query)

    def _leaf_in_query(self, leaf_value: int, query: HyperRange) -> bool:
        """Decode the rank and test true membership in the query rectangle."""
        return query.contains_point(self._point_of(leaf_value))
