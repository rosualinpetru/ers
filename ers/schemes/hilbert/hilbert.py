from typing import Set, List, Dict

from ers.schemes.common.emm import EMM
from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.hilbert_curve import HilbertCurve
from ers.structures.point import Point


class HilbertScheme(EMM):
    """
    A secure encrypted multi-map (EMM) scheme utilizing Hilbert curve mapping
    to transform multi-dimensional data into a single-dimensional space for indexing.

    This scheme enables efficient range queries by leveraging Hilbert curve ordering.
    """

    def __init__(self, emm_engine: EMMEngine):
        """
        Initializes the HilbertScheme instance.

        :param emm_engine: An instance of EMMEngine responsible for secure indexing and search operations.
        """
        super().__init__(emm_engine)
        self.order = max(emm_engine.DIMENSIONS_BITS)
        self.hc = HilbertCurve(self.order, self.dimensions)
        self.encrypted_db = None

    def _hilbert_plaintext_mm(self, plaintext_mm: Dict[Point, List[bytes]]) -> Dict[int, List[bytes]]:
        """
        Maps a given plaintext multi-map into a Hilbert curve space.

        :param plaintext_mm: A dictionary mapping Point objects to lists of plaintext values.
        :return: A dictionary mapping Hilbert distances to corresponding plaintext values.
        """
        for p in plaintext_mm.keys():
            assert p.dimensions() == self.dimensions

        return {self.hc.distance_from_point(p): plaintext_mm[p] for p in plaintext_mm.keys()}

    def search(self, trapdoors: Set[bytes]) -> Set[bytes]:
        """
        Searches for encrypted values corresponding to the given trapdoor tokens.

        :param trapdoors: A set of search tokens.
        :return: A set of encrypted results from the secure index.
        """
        results = set()

        if self.encrypted_db is None:
            return results

        for trapdoor in trapdoors:
            results = results.union(self.emm_engine.search(trapdoor, self.encrypted_db))

        return results
