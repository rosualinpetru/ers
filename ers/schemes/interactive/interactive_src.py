"""
Interactive double-index range search (``Logarithmic-SRC-i``, Demertzis et al.).

A two-round protocol that trades one extra communication round and client-side
state for precision: a first index maps the value domain to compact
document-index intervals, the client filters false positives locally, and a
second index returns only the surviving documents. The class is written over
an abstract 1-D *value domain* so that the plain 1-D, the Hilbert-linearised
and the native multi-dimensional variants share the whole protocol.
"""

import math
import secrets
import sys
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from tqdm import tqdm

from ers.schemes.common.emm import EMM
from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.hyperrange import HyperRange
from ers.structures.hyperrange_tree import HyperRangeTree
from ers.structures.point import Point
from ers.util.crypto.crypto import HashKDF
from ers.util.hyperrange.uniform_split_mid_overlap_divider import UniformSplitMidOverlapDivider
from ers.util.serialization.serialization import BytesToObject, ObjectToBytes


class InteractiveSRC(EMM):
    """
    The interactive, double-index ``Logarithmic-SRC-i`` scheme of Demertzis et al.
    (SIGMOD 2016), generalised so that the same code drives both the plain
    one-dimensional domain and (via :class:`InteractiveSRCHilbert`) a
    Hilbert-linearised multi-dimensional domain.

    Motivation
    ----------
    A single-round Single-Range-Cover (SRC) scheme answers a range query with one
    token, but that token covers the *smallest canonical range containing the
    query*, which is usually larger than the query itself. Every record in that
    canonical range — including the ones outside the query — is returned as a
    false positive. The larger the overshoot, the worse the precision.

    The interactive scheme removes most of those false positives by splitting the
    work across **two indices** ("an index inside an index") and **two rounds**:

    1. **First index — a map from the value domain to document-index ranges.**
       Records are sorted by their (1-D or Hilbert) value and given a contiguous
       *document index* ``0..N-1``; ties are shuffled. For every node of a
       TDAG built over the value domain we store, *not the documents*, but the
       compact list of ``(leaf_value, doc_lo, doc_hi)`` triples for the
       non-empty leaves beneath it. A first-round SRC query returns this tiny
       metadata blob. The client **filters** the triples locally, keeping only
       leaves whose value truly lies in the query, and is left with a tight set
       of document-index intervals.

    2. **Second index — a TDAG over document indices holding the real records.**
       In a second round the client asks only for those document-index
       intervals, and the server returns the actual (encrypted) documents.

    Why it helps
    ------------
    * **Precision.** The client filters false positives *between* the two rounds
      using the leaf values, so the second round targets (almost) exactly the
      matching records. For the Hilbert variant this is especially valuable: the
      first-round SRC covers the whole ``[min, max]`` Hilbert interval of the
      query (many false positives), yet filtering by each leaf's actual grid
      point discards the parts of the interval that fall outside the query
      rectangle.
    * **Storage.** The value index stores small integer triples instead of
      duplicating document payloads at every canonical range, so it is much
      smaller than a direct TdagSRC index over the domain.

    Costs
    -----
    * **An extra communication round** and the associated latency.
    * **Client-side local storage / state.** The client keeps both TDAGs (they
      are data-independent and could be recomputed, but keeping them avoids
      per-query work) and performs the inter-round filtering locally. This is the
      canonical "assume local storage to speed up the protocol" trade-off.

    This class exposes the low-level building blocks (``build_index`` and the two
    rounds) plus a convenience :meth:`query` that runs the whole protocol and
    records per-query metrics (tokens per round, rounds, filtered intervals).
    """

    #: Lossy with an SRC second round (the default); exact with a BRC second round.
    exact = False

    def __init__(self, emm_engine: EMMEngine, single_range_cover_round2: bool = True):
        """
        :param emm_engine: The EMM engine providing the cryptographic primitives.
        :param single_range_cover_round2: If ``True`` the second round uses SRC
            (one token per surviving interval, may overshoot → a few false
            positives). If ``False`` it uses BRC (more tokens, precision 1).
        """
        super().__init__(emm_engine)
        self.single_range_cover_round2 = single_range_cover_round2
        self.exact = not single_range_cover_round2

        # Encrypted indices (server-held).
        self.index1: Optional[Dict[bytes, bytes]] = None  # value-domain TDAG node  -> document-index metadata
        self.index2: Optional[Dict[bytes, bytes]] = None  # document-index TDAG node -> encrypted documents

        # Client-held state (local storage).
        # The value-domain structure is deliberately duck-typed (Any): the 1-D
        # and Hilbert variants use a HyperRangeTree, the native variant a
        # HyperRangeTreeProduct; both expose the descend/src surface the
        # protocol needs.
        self.tdag_val: Any = None  # TDAG over the value domain
        self.tdag_doc: Optional[HyperRangeTree] = None  # TDAG over the document-index domain
        self.n_documents = 0

        # Per-query metrics, populated by :meth:`query`.
        self.last_tokens_round1 = 0
        self.last_tokens_round2 = 0
        self.last_intervals = 0

    # ------------------------------------------------------------------ #
    # Hooks overridden by the Hilbert and native multi-dimensional variants.
    #
    # The base class runs the Logarithmic-SRC-i protocol over an abstract
    # *value domain*: every record is mapped to an integer value, values are
    # organised in a TDAG-like structure supporting descend/SRC, and the
    # client can test whether a value truly matches a query. Subclasses choose
    # the value domain:
    #   - InteractiveSRC (this class): the raw 1-D coordinate.
    #   - InteractiveSRCHilbert: the Hilbert distance of the point.
    #   - InteractiveSRCNative: the lexicographic rank of the point (native
    #     multi-dimensional domain, product-TDAG round one).
    # ------------------------------------------------------------------ #
    def _value_domain_bits(self) -> int:
        """Number of bits spanning the (1-D) value domain the records live in."""
        return self.emm_engine.DIMENSIONS_BITS[0]

    def _value_of(self, point: Point) -> int:
        """Map a data point to the integer value that orders the documents."""
        assert point.dimensions() == 1
        return point[0]

    def _build_value_tdag(self) -> Any:
        """
        Build the round-one structure over the value domain. Must support
        ``src`` (single covering node); leaf lookup goes through
        :meth:`_descend_value`. Typed ``Any`` because subclasses return either
        a :class:`HyperRangeTree` or a :class:`HyperRangeTreeProduct`.
        """
        return HyperRangeTree.init(
            HyperRange.from_bits([self._value_domain_bits()]),
            UniformSplitMidOverlapDivider(2),
        )

    def _descend_value(self, v: int) -> List[HyperRange]:
        """All value-TDAG nodes lying on the root-to-leaf path(s) of value ``v``."""
        return self.tdag_val.descend(HyperRange.from_point_coords([v]))

    def _round1_range(self, query: HyperRange) -> HyperRange:
        """The value-domain range whose SRC cover is fetched in round one."""
        assert query.dimensions == 1
        return query

    def _round1_cover_node(self, query: HyperRange) -> Optional[HyperRange]:
        """The single value-TDAG node covering the query (round-one token)."""
        return self.tdag_val.src(self._round1_range(query))

    def _leaf_in_query(self, leaf_value: int, query: HyperRange) -> bool:
        """Whether a value-domain leaf truly belongs to the query (client filter)."""
        return query.contains_point(Point([leaf_value]))

    # ------------------------------------------------------------------ #
    # Index construction.
    # ------------------------------------------------------------------ #
    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        """
        Build both indices and the client-side TDAGs.

        :param key: The master key; per-index sub-keys are derived from it.
        :param plaintext_mm: Map from data points to their document payloads.
        """
        k1, k2 = self._subkeys(key)

        # --- 1. Order documents by value, shuffling ties for security. --------
        entries: List[Tuple[int, bytes]] = []
        for point, vals in plaintext_mm.items():
            v = self._value_of(point)
            for payload in vals:
                entries.append((v, payload))

        # A random shuffle followed by a *stable* sort places equal-valued
        # documents in a uniformly random relative order (as the paper requires),
        # so the document-index of a record leaks nothing beyond its value rank.
        for i in reversed(range(1, len(entries))):
            j = secrets.randbelow(i + 1)
            entries[i], entries[j] = entries[j], entries[i]
        entries.sort(key=lambda e: e[0])
        self.n_documents = len(entries)

        # --- 2. Contiguous document-index interval per distinct value. --------
        value_to_interval: Dict[int, List[int]] = {}
        for idx, (v, _) in enumerate(entries):
            if v in value_to_interval:
                value_to_interval[v][1] = idx
            else:
                value_to_interval[v] = [idx, idx]

        # --- 3. First index: value-domain TDAG -> per-leaf doc-index metadata. -
        self.tdag_val = self._build_value_tdag()
        # Attach each leaf's (value, doc-index range) triple to every TDAG node
        # above it, by descending the tree once per distinct value. This is
        # O(#values * tree height) rather than O(#nodes * #values).
        node_triples: Dict[bytes, List[list]] = defaultdict(list)
        for v, iv in value_to_interval.items():
            for node_range in self._descend_value(v):
                node_triples[node_range.to_bytes()].append([v, iv[0], iv[1]])
        # One compact metadata blob per node (integers only, no document payloads).
        modified_db1 = {label: [ObjectToBytes(triples)] for label, triples in node_triples.items()}
        self.index1 = self.emm_engine.build_index(k1, modified_db1)

        # --- 4. Second index: document-index TDAG -> encrypted documents. -----
        doc_bits = max(1, math.ceil(math.log2(self.n_documents))) if self.n_documents > 1 else 1
        self.tdag_doc = HyperRangeTree.init(
            HyperRange.from_bits([doc_bits]),
            UniformSplitMidOverlapDivider(2),
        )
        modified_db2: Dict[bytes, List[bytes]] = defaultdict(list)
        for idx, (_, payload) in enumerate(tqdm(entries)):
            for rng in self.tdag_doc.descend(HyperRange.from_point_coords([idx])):
                modified_db2[rng.to_bytes()].append(payload)
        self.index2 = self.emm_engine.build_index(k2, modified_db2)

    # ------------------------------------------------------------------ #
    # The two rounds.
    # ------------------------------------------------------------------ #
    def trapdoor_round1(self, key: bytes, query: HyperRange) -> Set[bytes]:
        """Round-one token: the SRC cover of the query over the value TDAG."""
        k1, _ = self._subkeys(key)
        node = self._round1_cover_node(query)
        if node is None:
            return set()
        return {self.emm_engine.trapdoor(k1, node.to_bytes())}

    def filter_round1(self, key: bytes, encrypted_metadata: Set[bytes], query: HyperRange) -> List[Tuple[int, int]]:
        """
        Decrypt the round-one metadata, keep only leaves that truly match the
        query, and return the merged list of surviving document-index intervals.
        """
        k1, _ = self._subkeys(key)
        triples: List[List[int]] = []
        for blob in self.emm_engine.resolve(k1, encrypted_metadata):
            triples.extend(BytesToObject(blob))

        surviving = [(lo, hi) for (v, lo, hi) in triples if self._leaf_in_query(v, query)]
        return self._merge_intervals(surviving)

    def trapdoor_round2(self, key: bytes, intervals: List[Tuple[int, int]]) -> Set[bytes]:
        """Round-two tokens for the surviving document-index intervals."""
        if self.tdag_doc is None:
            raise ValueError("Index is not built yet!")
        _, k2 = self._subkeys(key)
        trapdoors = set()
        for lo, hi in intervals:
            rng = HyperRange.from_coords([lo], [hi])
            if self.single_range_cover_round2:
                node = self.tdag_doc.src(rng)
                covers = [node] if node is not None else []
            else:
                covers = self.tdag_doc.brc(rng)
            for c in covers:
                trapdoors.add(self.emm_engine.trapdoor(k2, c.to_bytes()))
        return trapdoors

    def search_index(self, trapdoors: Set[bytes], index: Optional[Dict[bytes, bytes]]) -> Set[bytes]:
        """
        Searches one of the two encrypted indices with a set of trapdoors.

        The single-round :meth:`EMM.search` does not apply to this protocol:
        each round targets a different index.

        :param trapdoors: The tokens of the round.
        :param index: :attr:`index1` or :attr:`index2`.
        :return: The encrypted entries matching any token.
        :raises ValueError: If the index has not been built yet.
        """
        if index is None:
            raise ValueError("Index is not built yet!")
        results: Set[bytes] = set()
        for trapdoor in trapdoors:
            results |= self.emm_engine.search(trapdoor, index)
        return results

    def search(self, trapdoors: Set[bytes]) -> Set[bytes]:
        """
        Not applicable: the protocol is two-round. Use :meth:`query`, or
        :meth:`search_index` with the index of the round.

        :raises NotImplementedError: Always.
        """
        raise NotImplementedError("InteractiveSRC is a two-round protocol: use query() or search_index()")

    def query(self, key: bytes, query: HyperRange) -> Set[bytes]:
        """
        Run the full two-round interactive protocol and return the decrypted
        documents. Side-effect: records per-query metrics on ``self``.
        """
        k1, k2 = self._subkeys(key)

        # Round 1: fetch and locally filter the value-domain metadata.
        td1 = self.trapdoor_round1(key, query)
        enc1 = self.search_index(td1, self.index1)
        intervals = self.filter_round1(key, enc1, query)

        # Round 2: fetch the actual documents for the surviving intervals.
        td2 = self.trapdoor_round2(key, intervals)
        enc2 = self.search_index(td2, self.index2)
        documents = self.emm_engine.resolve(k2, enc2)

        self.last_tokens_round1 = len(td1)
        self.last_tokens_round2 = len(td2)
        self.last_intervals = len(intervals)
        return documents

    def query_with_metrics(self, key: bytes, query: HyperRange):
        """
        Run the protocol and return ``(documents, metrics)`` where ``metrics``
        breaks down token counts and per-phase timings across the two rounds, in
        the same shape the benchmark harness records for single-round schemes.
        """
        k1, k2 = self._subkeys(key)

        t0 = time.perf_counter()
        td1 = self.trapdoor_round1(key, query)
        t1 = time.perf_counter()
        enc1 = self.search_index(td1, self.index1)
        t2 = time.perf_counter()
        intervals = self.filter_round1(key, enc1, query)
        t3 = time.perf_counter()
        td2 = self.trapdoor_round2(key, intervals)
        t4 = time.perf_counter()
        enc2 = self.search_index(td2, self.index2)
        t5 = time.perf_counter()
        documents = self.emm_engine.resolve(k2, enc2)
        t6 = time.perf_counter()

        metrics = {
            # token generation only (both rounds), comparable to trapdoor_time
            "trapdoor_time": (t1 - t0) + (t4 - t3),
            "search_time": (t2 - t1) + (t5 - t4),
            "resolve_time": (t6 - t5),
            "filter_time": (t3 - t2),
            "trapdoor_count": len(td1) + len(td2),
            "trapdoor_count_round1": len(td1),
            "trapdoor_count_round2": len(td2),
            "search_count": len(enc1) + len(enc2),
            "rounds": 2,
        }
        return documents, metrics

    # ------------------------------------------------------------------ #
    # Sizes (for benchmarking).
    # ------------------------------------------------------------------ #
    @staticmethod
    def _size_bytes(index: Optional[Dict[bytes, bytes]]) -> int:
        if index is None:
            raise ValueError("Index is not built yet!")
        return sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in index.items())

    def index1_size_bytes(self) -> int:
        """Size proxy (``sys.getsizeof`` of keys and values) of the value-domain index."""
        return self._size_bytes(self.index1)

    def index2_size_bytes(self) -> int:
        """Size proxy (``sys.getsizeof`` of keys and values) of the document index."""
        return self._size_bytes(self.index2)

    # ------------------------------------------------------------------ #
    # Helpers.
    # ------------------------------------------------------------------ #
    @staticmethod
    def _subkeys(key: bytes) -> Tuple[bytes, bytes]:
        """Derive independent sub-keys for the two indices so their tokens never collide."""
        return HashKDF(key, "interactive-index-1"), HashKDF(key, "interactive-index-2")

    @staticmethod
    def _merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Sort and merge overlapping/adjacent ``[lo, hi]`` document-index intervals."""
        if not intervals:
            return []
        intervals = sorted(intervals)
        merged = [list(intervals[0])]
        for lo, hi in intervals[1:]:
            if lo <= merged[-1][1] + 1:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        return [(lo, hi) for lo, hi in merged]
