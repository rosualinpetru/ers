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

    def _hilbert_ranges(self, p1: Point, p2: Point, segment_gap_tolerance: float, downscale_percentage: int) -> List[tuple[int, int]]:
        (reduced_edge_bits, p1, p2) = _hilbert_downscale(self.edge_bits, downscale_percentage, p1, p2)
        hc = HilbertCurve(self.edge_bits - reduced_edge_bits, 2)

        perimeter_points = _perimeter_points(p1, p2)
        hilbert_perimeter_indices = sorted([hc.distance_from_point([point.x, point.y]) for point in perimeter_points])

        segment_gap_threshold = _area(p1, p2) * segment_gap_tolerance

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
                    if hilbert_perimeter_indices[i + 1] - hilbert_perimeter_indices[i] >= segment_gap_threshold:
                        break  # Finalize the current range
                    else:
                        end_range = hilbert_perimeter_indices[i + 1]  # Include the point despite being outside
                else:
                    end_range = hilbert_perimeter_indices[i + 1]  # Point is inside, extend the range

                i += 1

            ranges.append((start_range, end_range))  # Finalize and store the current range
            i += 1

        return _hilbert_upscale(reduced_edge_bits, ranges)

    def _hilbert_range_src(self, p1: Point, p2: Point, downscale_percentage: int) -> tuple[int, int]:
        (reduced_edge_bits, p1, p2) = _hilbert_downscale(self.edge_bits, downscale_percentage, p1, p2)
        hc = HilbertCurve(self.edge_bits - reduced_edge_bits, 2)

        perimeter_points = _perimeter_points(p1, p2)
        hilbert_perimeter_indices = sorted([hc.distance_from_point([point.x, point.y]) for point in perimeter_points])

        ranges = [(min(hilbert_perimeter_indices), max(hilbert_perimeter_indices))]

        return _hilbert_upscale(reduced_edge_bits, ranges)[0]


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

def _hilbert_downscale(edge_bits: int, downscale_percentage: int, p1: Point, p2: Point) -> tuple[int, Point, Point]:
    reduced_bits = math.floor(downscale_percentage / 100 * edge_bits)

    def downscale_point(p: Point):
        half_x = p.x // 2
        x = half_x + (p.x % half_x) if half_x != 0 else 0
        half_y = p.y // 2
        y = half_y + (p.y % half_y) if half_y != 0 else 0

        return Point(x, y)

    for _ in range(reduced_bits):
        p1 = downscale_point(p1)
        p2 = downscale_point(p2)

    reduced_max_coordinate = 1 << (edge_bits - reduced_bits)

    if reduced_bits > 0:
        p1.x = max(0, p1.x - 1)
        p1.y = max(0, p1.y - 1)

        p2.x = min(reduced_max_coordinate, p2.x + 1)
        p2.y = min(reduced_max_coordinate, p2.y + 1)

    return reduced_bits, p1, p2


def _hilbert_upscale(reduced_edge_bits: int, ranges: List[tuple[int, int]]) -> List[tuple[int, int]]:
    upscale_factor = reduced_edge_bits * 2
    upscaled_ranges = []

    for int_range in ranges:
        start_curve_point = int_range[0] << upscale_factor
        end_curve_point = int_range[1] << upscale_factor

        upscaled_ranges.append((start_curve_point, end_curve_point))

    return upscaled_ranges
