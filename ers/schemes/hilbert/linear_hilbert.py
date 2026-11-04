"""
Linear scheme over the Hilbert curve.

Every point is indexed under its own curve distance, and a query is answered
with one token per distance in each Hilbert segment of the query. Index size,
token count and security are identical to the native :class:`Linear` scheme
(both issue one token per query point); only the enumeration order differs.
"""

from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.schemes.common.emm import EMM
from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.hilbert_curve import HilbertCurve
from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point


class LinearHilbert(EMM):
    """A range-search scheme indexing each Hilbert distance under its own label."""

    exact = True

    def __init__(self, emm_engine: EMMEngine):
        """
        :param emm_engine: The engine providing the cryptographic primitives.
        """
        super().__init__(emm_engine)
        self.order = max(emm_engine.DIMENSIONS_BITS)
        self.hc = HilbertCurve(self.order, self.dimensions)

    @staticmethod
    def _label(distance: int) -> bytes:
        """The index label of a curve distance: its singleton 1-D range."""
        return HyperRange.from_point_coords([distance]).to_bytes()

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]) -> None:
        """
        Builds the encrypted index with one postings list per curve distance.

        :param key: The secret key used to encrypt the index.
        :param plaintext_mm: A mapping from data points to their records.
        """
        modified_db: Dict[bytes, List[bytes]] = defaultdict(list)
        for point, vals in tqdm(plaintext_mm.items()):
            assert point.dimensions() == self.dimensions
            modified_db[self._label(self.hc.distance_from_point(point))].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRange, merging_tolerance: float = 0) -> Set[bytes]:
        """
        Generates one token per curve distance in the Hilbert segments of the query.

        :param key: The secret key used to derive the tokens.
        :param query: The range to search.
        :param merging_tolerance: Segment-merging tolerance (see
            :meth:`HilbertCurve.brc_with_merging`); 0 keeps the cover exact.
        :return: The set of search tokens.
        """
        assert query.dimensions == self.dimensions
        trapdoors: Set[bytes] = set()
        for lo, hi in self.hc.brc_with_merging(query, merging_tolerance):
            for distance in range(lo, hi + 1):
                trapdoors.add(self.emm_engine.trapdoor(key, self._label(distance)))
        return trapdoors
