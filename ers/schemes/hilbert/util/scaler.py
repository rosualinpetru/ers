"""
Space downscaling for Hilbert queries (experimental; not wired into any scheme).

Moten's empirical technique for very high curve orders: shrink the query by
dropping low-order bits of every coordinate, compute the Hilbert segments on
the coarser curve, and lift the resulting intervals back to the original
order. The lifted cover is a superset of the exact one (the shrunken query is
widened by one cell per dimension to avoid false negatives), so the technique
trades precision for segment-computation time. See the report's discussion.
"""

from typing import List, Tuple

from ers.structures.hyperrange import HyperRange


class Scaler:
    """Downscales queries by whole bits and upscales Hilbert intervals back."""

    def __init__(self, bits: int, dimensions: int):
        """
        :param bits: The per-dimension bit length of the original domain.
        :param dimensions: The number of dimensions of the domain.
        """
        self.bits = bits
        self.dimensions = dimensions

    def downscale(self, bits: int, query: HyperRange) -> HyperRange:
        """
        Drops ``bits`` low-order bits from every coordinate of the query and
        widens the result by one cell per dimension (clamped to the reduced
        domain) so that no point of the original query is lost.

        :param bits: The number of bits of precision to drop.
        :param query: The query in the original domain.
        :return: The widened query in the reduced domain.
        """
        if bits <= 0:
            return query

        reduced_max_coordinate = (1 << (self.bits - bits)) - 1
        start = [max(0, (c >> bits) - 1) for c in query.start.coords()]
        end = [min(reduced_max_coordinate, (c >> bits) + 1) for c in query.end.coords()]
        return HyperRange.from_coords(start, end)

    def upscale(self, bits: int, ranges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        Lifts Hilbert intervals of the reduced curve back to the original
        curve. Dropping ``bits`` bits per dimension drops ``bits * dimensions``
        bits of curve distance, so each reduced cell expands to a block of
        ``2 ** (bits * dimensions)`` consecutive distances.

        :param bits: The number of bits of precision that were dropped.
        :param ranges: Intervals of reduced-curve distances.
        :return: The corresponding intervals of original-curve distances.
        """
        shift = bits * self.dimensions
        return [(lo << shift, ((hi + 1) << shift) - 1) for lo, hi in ranges]
