"""
Linear range-search scheme.

The baseline scheme of Falzon et al.: every data point is indexed under its own
label and a range query is answered by one token per point of the query. It is
exact and needs the smallest possible index (one entry per record), but the
token count grows with the query *volume*, which makes it the reference point
every structured scheme has to beat.
"""

from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.schemes.common.emm import EMM
from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point


class Linear(EMM):
    """A range-search scheme that indexes each data point under its own label."""

    exact = True

    @staticmethod
    def _label(point: Point) -> bytes:
        """The index label of a point: its singleton range."""
        return HyperRange.from_point(point).to_bytes()

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]) -> None:
        """
        Builds the encrypted index with one postings list per point.

        :param key: The secret key used to encrypt the index.
        :param plaintext_mm: A mapping from data points to their records.
        """
        modified_db: Dict[bytes, List[bytes]] = defaultdict(list)
        for point, vals in tqdm(plaintext_mm.items()):
            assert point.dimensions() == self.dimensions
            modified_db[self._label(point)].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRange) -> Set[bytes]:
        """
        Generates one token per point contained in the query.

        :param key: The secret key used to derive the tokens.
        :param query: The range to search.
        :return: The set of search tokens, one per query point.
        """
        assert query.dimensions == self.dimensions
        return {self.emm_engine.trapdoor(key, self._label(point)) for point in query.points()}
