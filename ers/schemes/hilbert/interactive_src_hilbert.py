"""
Interactive double-index scheme over the Hilbert curve.

The value that orders the documents is the point's Hilbert distance; round one
covers the ``[min, max]`` curve interval of the query with one TDAG token, and
the client discards every leaf whose decoded grid point lies outside the query
rectangle before asking for documents.
"""

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.interactive.interactive_src import InteractiveSRC
from ers.structures.hilbert_curve import HilbertCurve
from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point


class InteractiveSRCHilbert(InteractiveSRC):
    """
    The interactive double-index scheme (:class:`InteractiveSRC`) applied to a
    Hilbert-linearised multi-dimensional domain.

    This is the multi-dimensional extension the report calls for. The value that
    orders documents is the point's **Hilbert distance**, so the whole
    ``Logarithmic-SRC-i`` machinery runs over the 1-D Hilbert index. The payoff is
    concentrated in the inter-round filter: a non-interactive Hilbert SRC has to
    cover the entire ``[min, max]`` Hilbert interval of a query and therefore
    returns every point the curve visits between those two indices — including
    the (often many) points that lie outside the query rectangle. Here, round one
    returns only compact document-index metadata, and the client discards the
    leaves whose **actual grid point** falls outside the rectangle before asking
    for any documents. Interaction thus converts the Hilbert curve's structural
    false positives into a cheap local filtering step.
    """

    def __init__(self, emm_engine: EMMEngine, single_range_cover_round2: bool = True):
        super().__init__(emm_engine, single_range_cover_round2)
        self.dimensions = emm_engine.dimensions
        self.order = max(emm_engine.DIMENSIONS_BITS)
        self.hc = HilbertCurve(self.order, self.dimensions)

    def _value_domain_bits(self) -> int:
        # The Hilbert index spans d * n bits (d dimensions, order n).
        return self.dimensions * self.order

    def _value_of(self, point: Point) -> int:
        # Order documents by Hilbert distance rather than a raw coordinate.
        assert point.dimensions() == self.dimensions
        return self.hc.distance_from_point(point)

    def _round1_range(self, query: HyperRange) -> HyperRange:
        # Round one covers the single [min, max] Hilbert interval of the query.
        lo, hi = self.hc.src(query)
        return HyperRange.from_coords([lo], [hi])

    def _leaf_in_query(self, leaf_value: int, query: HyperRange) -> bool:
        # A Hilbert leaf matches only if its decoded grid point is truly inside
        # the query rectangle — this is what filters out the curve's excursions
        # outside the query between the min and max Hilbert indices.
        return query.contains_point(self.hc.point_from_distance(leaf_value))
