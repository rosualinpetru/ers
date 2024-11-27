import math
from typing import Dict, List, Set

from hilbertcurve.hilbertcurve import HilbertCurve

from ers.schemes.common.emm import EMM
from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.point import Point
from ers.structures.rect import Rect


class Hilbert(EMM):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.encrypted_db = None

        self.edge_bits = math.ceil(math.log2(max(emm_engine.MAX_X, emm_engine.MAX_Y)))
        self.dimension = 2
        self.hc = HilbertCurve(self.edge_bits, self.dimension)

    def search(self, trapdoors: Set[bytes]) -> Set[bytes]:
        results = set()

        if self.encrypted_db is None:
            return results

        for trapdoor in trapdoors:
            results = results.union(self.emm_engine.search(trapdoor, self.encrypted_db))

        return results

    def _hilbert_plaintext_mm(self, plaintext_mm: Dict[Point, List[bytes]]):
        return {self.hc.distance_from_point([pt.x, pt.y]): plaintext_mm[pt] for pt in plaintext_mm.keys()}

    def _hilbert_ranges(self, p1: Point, p2: Point, false_positive_tolerance_factor: float, downscale: bool) -> List[tuple[int, int]]:
        hc = self.hc
        reduced_edge_bits = 0
        if downscale:
            (reduced_edge_bits, p1, p2) = _hilbert_downscale(self.edge_bits, p1, p2)
            hc = HilbertCurve(self.edge_bits - reduced_edge_bits, 2)

        perimeter_points = _perimeter_points(p1, p2)
        hilbert_perimeter_indices = sorted([hc.distance_from_point([point.x, point.y]) for point in perimeter_points])

        false_positive_tolerance = _area(p1, p2) * false_positive_tolerance_factor

        ranges = []
        i = 0
        while i < len(hilbert_perimeter_indices):
            start_range = hilbert_perimeter_indices[i]
            end_range = start_range

            while i + 1 < len(hilbert_perimeter_indices):  # Start a new range
                if hilbert_perimeter_indices[i + 1] == hilbert_perimeter_indices[i] + 1:  # Check if the next index is contiguous
                    end_range = hilbert_perimeter_indices[i + 1]
                    i += 1
                    continue

                [x, y] = hc.point_from_distance(hilbert_perimeter_indices[i] + 1)  # Calculate the point at the next distance

                if not Rect(p1, p2).contains_point(Point(x, y)):  # If it's outside the rectangle, check tolerance
                    if hilbert_perimeter_indices[i + 1] - hilbert_perimeter_indices[i] >= false_positive_tolerance:
                        break  # Finalize the current range
                    else:
                        end_range = hilbert_perimeter_indices[i + 1]  # Include the point despite being outside
                else:
                    end_range = hilbert_perimeter_indices[i + 1]  # Point is inside, extend the range

                i += 1

            ranges.append((start_range, end_range))  # Finalize and store the current range
            i += 1

        if downscale:
            return _hilbert_upscale(reduced_edge_bits, ranges)

        return ranges


def _area(p1: Point, p2: Point) -> int:
    width = p2.x - p1.x
    height = p2.y - p1.y

    return width * height


def _perimeter_points(p1: Point, p2: Point) -> List[Point]:
    perimeter_points = []
    for x in range(p1.x, p2.x + 1):
        perimeter_points.append(Point(x, p1.y))
        perimeter_points.append(Point(x, p2.y))

    for y in range(p1.y + 1, p2.y):
        perimeter_points.append(Point(p1.x, y))
        perimeter_points.append(Point(p2.x, y))

    return perimeter_points


# Currently, there is no downscaling performed
def _hilbert_downscale(edge_bits: int, p1: Point, p2: Point) -> tuple[int, Point, Point]:
    return 0, p1, p2


def _hilbert_upscale(reduced_edge_bits: int, ranges: List[tuple[int, int]]) -> List[tuple[int, int]]:
    return ranges
