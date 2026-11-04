"""
Hilbert-linearised range-search schemes.

A Hilbert curve of order ``n`` over ``d`` dimensions visits every cell of the
``2**n``-wide grid exactly once and preserves locality, so mapping each point
to its curve distance reduces the multi-attribute domain to the 1-D interval
``[0, 2**(d*n))``, where the 1-D structures of Falzon et al. apply unchanged.

The catch is on the query side: an axis-aligned rectangle does not map to one
curve interval but shatters into several disjoint *segments*
(:meth:`HilbertCurve.brc_with_merging`). The two cover rules deal with that
differently:

* :class:`HilbertBestRangeCover` takes the Best Range Cover of **every segment**
  over the 1-D tree -- exact at merging tolerance 0, more tokens than the native
  scheme because a rectangle is many segments;
* :class:`HilbertSingleRangeCover` covers the single interval from the
  **minimum to the maximum** curve distance of the rectangle with one node --
  one token, plus every curve excursion outside the rectangle as false positives.
"""

from typing import Dict, Iterable, List, Set

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.common.structured_scheme import StructuredScheme
from ers.structures.hilbert_curve import HilbertCurve
from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point


def hilbert_project(hc: HilbertCurve, plaintext_mm: Dict[Point, List[bytes]]) -> Dict[Point, List[bytes]]:
    """
    Maps a multi-map keyed by grid points to one keyed by 1-D curve distances.

    :param hc: The curve to project with.
    :param plaintext_mm: A mapping from ``d``-dimensional points to records.
    :return: A mapping from the singleton points ``Point([distance])`` to records.
    """
    return {Point([hc.distance_from_point(p)]): vals for p, vals in plaintext_mm.items()}


class HilbertScheme(StructuredScheme):
    """
    A structure-plus-cover scheme whose indexing domain is the Hilbert curve.

    The curve order is the largest per-dimension bit length, so every grid
    point has a distinct distance; the 1-D indexing domain spans
    ``dimensions * order`` bits (:attr:`hilbert_bits`).
    """

    def __init__(self, emm_engine: EMMEngine):
        """
        :param emm_engine: The engine providing the cryptographic primitives.
        """
        super().__init__(emm_engine)
        self.order = max(emm_engine.DIMENSIONS_BITS)
        self.hc = HilbertCurve(self.order, self.dimensions)
        #: Bit length of the 1-D Hilbert domain the structure is built over.
        self.hilbert_bits = self.dimensions * self.order

    def _index_domain(self, plaintext_mm: Dict[Point, List[bytes]]) -> Dict[Point, List[bytes]]:
        return hilbert_project(self.hc, plaintext_mm)

    @staticmethod
    def _interval(lo: int, hi: int) -> HyperRange:
        """The 1-D range ``[lo, hi]`` of curve distances."""
        return HyperRange.from_coords([lo], [hi])


class HilbertBestRangeCover(HilbertScheme):
    """
    Cover rule: the Best Range Cover of each Hilbert segment of the query.

    Exact at merging tolerance 0. A positive tolerance merges segments across
    short curve excursions outside the query (fewer tokens, false positives).
    """

    exact = True

    def _cover(self, query: HyperRange, merging_tolerance: float = 0) -> Iterable[HyperRange]:
        structure = self._require_structure()
        cover: List[HyperRange] = []
        for lo, hi in self.hc.brc_with_merging(query, merging_tolerance):
            cover.extend(structure.brc(self._interval(lo, hi)))
        return cover

    def trapdoor(self, key: bytes, query: HyperRange, merging_tolerance: float = 0) -> Set[bytes]:
        """
        Generates the tokens of the Best Range Cover of every Hilbert segment of the query.

        :param key: The secret key used to derive the tokens.
        :param query: The range to search, in the native domain.
        :param merging_tolerance: Maximum length of a curve excursion outside
            the query, as a fraction of the query volume, across which two
            segments are merged. 0 disables merging and keeps the cover exact.
        :return: The set of search tokens.
        """
        assert query.dimensions == self.dimensions
        return {self.emm_engine.trapdoor(key, rng.to_bytes()) for rng in self._cover(query, merging_tolerance)}


class HilbertSingleRangeCover(HilbertScheme):
    """
    Cover rule: the single structure node containing the whole ``[min, max]``
    curve interval of the query. One token; every point the curve visits
    between the two extremes but outside the rectangle is a false positive.
    """

    exact = False

    def _cover(self, query: HyperRange) -> Iterable[HyperRange]:
        lo, hi = self.hc.src(query)
        rng = self._require_structure().src(self._interval(lo, hi))
        if rng is None:
            raise ValueError(f"Query {query} is not contained in the indexed domain")
        return [rng]
