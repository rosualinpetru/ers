"""Shared helpers for the test suite: small deterministic datasets and queries."""

import itertools
import random
from typing import Dict, List

from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point


def sparse_dataset(bits: int, dimensions: int, n_points: int, seed: int = 0) -> Dict[Point, List[bytes]]:
    """A small random multi-map over a ``2**bits`` per-dimension domain."""
    rng = random.Random(seed)
    bound = 2**bits
    mm: Dict[Point, List[bytes]] = {}
    for _ in range(n_points):
        coords = [rng.randrange(bound) for _ in range(dimensions)]
        p = Point(coords)
        mm.setdefault(p, []).append(("d" + "_".join(map(str, coords))).encode())
    return mm


def random_queries(bits: int, dimensions: int, n: int, seed: int = 1) -> List[HyperRange]:
    """A list of random axis-aligned range queries over the domain."""
    rng = random.Random(seed)
    bound = 2**bits
    out = []
    for _ in range(n):
        lo, hi = [], []
        for _ in range(dimensions):
            a, b = sorted((rng.randrange(bound), rng.randrange(bound)))
            lo.append(a)
            hi.append(b)
        out.append(HyperRange.from_coords(lo, hi))
    return out


def true_positives(query: HyperRange, mm: Dict[Point, List[bytes]]) -> set:
    """The exact set of document payloads whose point lies inside the query."""
    tp = set()
    ranges = [range(query.start[i], query.end[i] + 1) for i in range(query.dimensions)]
    for coords in itertools.product(*ranges):
        p = Point(list(coords))
        if p in mm:
            tp |= set(mm[p])
    return tp
