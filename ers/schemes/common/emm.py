"""
Encrypted Multi-Map (EMM) scheme base class.

Every range-search scheme in :mod:`ers.schemes` is an :class:`EMM`: a thin
object that owns an :class:`EMMEngine` (the cryptographic core), builds an
encrypted index from a plaintext multi-map of points to records, turns a range
query into search tokens (trapdoors), and resolves the encrypted results. The
server-side search is identical for every single-round scheme and therefore
lives here; schemes only decide *which labels* a point is indexed under and
*which labels* a query asks for.
"""

from typing import Dict, List, Optional, Set

from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point

from .emm_engine import EMMEngine


class EMM:
    """
    Base class for range-search schemes over an encrypted multi-map.

    Subclasses implement :meth:`build_index` and :meth:`trapdoor`; the shared
    :meth:`setup`, :meth:`search` and :meth:`resolve` complete the five-step
    protocol (setup, index construction, trapdoor generation, search, result
    resolution).
    """

    #: Whether :meth:`search` can return only true positives. Exact schemes
    #: (the linear scheme and every Best-Range-Cover scheme at merging
    #: tolerance 0) have precision 1 by construction, so the benchmark harness
    #: does not measure it for them. Lossy schemes set this to ``False``.
    exact: bool = True

    def __init__(self, emm_engine: EMMEngine):
        """
        :param emm_engine: The engine providing key setup, index encryption,
            trapdoor derivation and result decryption.
        """
        self.emm_engine = emm_engine
        self.dimensions = emm_engine.dimensions
        #: The server-held encrypted index, populated by :meth:`build_index`.
        self.encrypted_db: Optional[Dict[bytes, bytes]] = None

    def setup(self, security_parameter: int) -> bytes:
        """
        Generates the client's secret key.

        :param security_parameter: The key length in bytes.
        :return: A uniformly random key.
        """
        return self.emm_engine.setup(security_parameter)

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]) -> None:
        """
        Builds the encrypted index over a plaintext multi-map.

        :param key: The secret key returned by :meth:`setup`.
        :param plaintext_mm: A mapping from data points to the records stored at them.
        :raises NotImplementedError: Always; subclasses must override.
        """
        raise NotImplementedError

    def trapdoor(self, key: bytes, query: HyperRange) -> Set[bytes]:
        """
        Generates the search tokens answering a range query.

        :param key: The secret key returned by :meth:`setup`.
        :param query: The axis-aligned range to search.
        :return: The set of tokens to send to the server.
        :raises NotImplementedError: Always; subclasses must override.
        """
        raise NotImplementedError

    def search(self, trapdoors: Set[bytes]) -> Set[bytes]:
        """
        Executes the server-side search: the union of the postings of every token.

        :param trapdoors: The tokens produced by :meth:`trapdoor`.
        :return: The encrypted records matching any of the tokens.
        :raises ValueError: If the index has not been built yet.
        """
        encrypted_db = self._require_index()
        results: Set[bytes] = set()
        for trapdoor in trapdoors:
            results |= self.emm_engine.search(trapdoor, encrypted_db)
        return results

    def resolve(self, key: bytes, results: Set[bytes]) -> Set[bytes]:
        """
        Decrypts the records returned by :meth:`search`.

        :param key: The secret key returned by :meth:`setup`.
        :param results: The encrypted records retrieved from the index.
        :return: The plaintext records.
        """
        return self.emm_engine.resolve(key, results)

    def _require_index(self) -> Dict[bytes, bytes]:
        """
        :return: The encrypted index.
        :raises ValueError: If :meth:`build_index` has not been called yet.
        """
        if self.encrypted_db is None:
            raise ValueError("Index is not built yet!")
        return self.encrypted_db
