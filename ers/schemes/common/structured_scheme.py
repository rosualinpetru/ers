"""
Structure-plus-cover range-search schemes.

All tree-based schemes of Falzon et al. -- and their Hilbert-linearised and
data-dependent variants -- share one shape: each record is indexed under the
label of every node of a *range-supporting structure* that contains its point,
and a query is answered by the tokens of a *cover* of the query, a set of nodes
whose union contains it. What distinguishes the schemes is only

1. which structure is built (:meth:`StructuredScheme._build_structure`), and
2. which cover rule is used: the **Best Range Cover** (the minimal set of nodes
   tiling the query exactly; :class:`BestRangeCover`) or the **Single Range
   Cover** (the one smallest node containing the whole query;
   :class:`SingleRangeCover`).

:class:`StructuredScheme` implements everything else once.
"""

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Protocol, Set

from tqdm import tqdm

from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point

from .emm import EMM
from .emm_engine import EMMEngine


class RangeSupportingStructure(Protocol):
    """
    The interface a structure must offer to be indexed with: the Definition 4
    "range-supporting data structure" of Falzon et al., with both cover rules.
    Satisfied by :class:`~ers.structures.hyperrange_tree.HyperRangeTree` and
    :class:`~ers.structures.hyperrange_tree_product.HyperRangeTreeProduct`.
    """

    def descend(self, rng: HyperRange) -> List[HyperRange]:
        """All canonical ranges containing ``rng`` (the root-to-leaf path(s))."""
        ...

    def brc(self, rng: HyperRange) -> List[HyperRange]:
        """The minimal set of canonical ranges whose union is exactly ``rng``."""
        ...

    def src(self, rng: HyperRange) -> Optional[HyperRange]:
        """The smallest single canonical range containing ``rng``, if any."""
        ...


class StructuredScheme(EMM):
    """
    A range-search scheme that indexes points under the nodes of a
    range-supporting structure and answers queries with a cover of that
    structure.

    Subclasses provide :meth:`_build_structure` and :meth:`_cover`; the
    Hilbert-linearised schemes additionally override :meth:`_index_domain` to
    project points onto the curve before indexing.
    """

    def __init__(self, emm_engine: EMMEngine):
        """
        :param emm_engine: The engine providing the cryptographic primitives.
        """
        super().__init__(emm_engine)
        #: The client-held range-supporting structure, built by :meth:`build_index`.
        self.structure: Optional[RangeSupportingStructure] = None

    # ------------------------------------------------------------------ #
    # Hooks.
    # ------------------------------------------------------------------ #
    def _index_domain(self, plaintext_mm: Dict[Point, List[bytes]]) -> Dict[Point, List[bytes]]:
        """
        Maps the data points to the domain the structure is built over.

        The default is the identity (native multi-dimensional domain); the
        Hilbert schemes map every point to its 1-D curve distance.
        """
        return plaintext_mm

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        """
        Builds the range-supporting structure over the indexing domain.

        :param indexed_mm: The multi-map as returned by :meth:`_index_domain`
            (data-dependent dividers read the point distribution from it).
        """
        raise NotImplementedError

    def _cover(self, query: HyperRange) -> Iterable[HyperRange]:
        """
        The canonical ranges whose tokens answer ``query``.

        :param query: A range in the *native* domain.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # Protocol.
    # ------------------------------------------------------------------ #
    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]) -> None:
        """
        Builds the structure and encrypts one postings list per structure node.

        Every record is stored under *each* node on its point's root-to-leaf
        path(s), so a token for a node retrieves its whole subtree.

        :param key: The secret key used to encrypt the index.
        :param plaintext_mm: A mapping from data points to their records.
        """
        for point in plaintext_mm:
            assert point.dimensions() == self.dimensions

        indexed_mm = self._index_domain(plaintext_mm)
        self.structure = self._build_structure(indexed_mm)

        modified_db: Dict[bytes, List[bytes]] = defaultdict(list)
        for point, vals in tqdm(indexed_mm.items()):
            for rng in self.structure.descend(HyperRange.from_point(point)):
                modified_db[rng.to_bytes()].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRange) -> Set[bytes]:
        """
        Generates one token per canonical range in the cover of the query.

        :param key: The secret key used to derive the tokens.
        :param query: The range to search, in the native domain.
        :return: The set of search tokens.
        :raises ValueError: If the index has not been built yet.
        """
        assert query.dimensions == self.dimensions
        self._require_structure()
        return {self.emm_engine.trapdoor(key, rng.to_bytes()) for rng in self._cover(query)}

    def _require_structure(self) -> RangeSupportingStructure:
        """
        :return: The range-supporting structure.
        :raises ValueError: If :meth:`build_index` has not been called yet.
        """
        if self.structure is None:
            raise ValueError("Index is not built yet!")
        return self.structure


class BestRangeCover(StructuredScheme):
    """
    Cover rule: the **Best Range Cover** -- the minimal set of structure nodes
    whose union is exactly the query. Exact (no false positives), one token per
    cover node.
    """

    exact = True

    def _cover(self, query: HyperRange) -> Iterable[HyperRange]:
        return self._require_structure().brc(query)


class SingleRangeCover(StructuredScheme):
    """
    Cover rule: the **Single Range Cover** -- the one smallest structure node
    containing the whole query. Exactly one token, at the price of the false
    positives lying in the node but outside the query.
    """

    exact = False

    def _cover(self, query: HyperRange) -> Iterable[HyperRange]:
        rng = self._require_structure().src(query)
        if rng is None:
            raise ValueError(f"Query {query} is not contained in the indexed domain")
        return [rng]
