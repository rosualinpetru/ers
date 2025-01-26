from typing import List, Tuple, Iterable

from hilbertcurve.hilbertcurve import HilbertCurve as Hc

from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point


class HilbertCurve:
    def __init__(self, order: int, dimensions: int):
        self.hc = Hc(order, dimensions)
        self.order = order  # edge bits
        self.dimensions = dimensions

    def distance_from_point(self, point: Point) -> int:
        return self.hc.distance_from_point(point.coords())

    def point_from_distance(self, distance: int) -> Point:
        return Point(list(self.hc.point_from_distance(distance)))

    def distances_from_points(self, points: Iterable[Point]) -> Iterable[int]:
        return [self.distance_from_point(point) for point in points]

    def points_from_distances(self, distances: Iterable[int]) -> Iterable[Point]:
        return [self.point_from_distance(distance) for distance in distances]

    def brc(self, rng: HyperRange):
        return self.brc_with_merging(rng, 0)

    def brc_with_merging(self, rng: HyperRange, segment_gap_tolerance: float) -> List[Tuple[int, int]]:
        perimeter_points = rng.boundary_points()
        perimeter_distances = sorted(self.distances_from_points(perimeter_points))

        segment_gap_threshold = rng.volume() * segment_gap_tolerance

        ranges = []
        i = 0
        while i < len(perimeter_distances):
            start_range = perimeter_distances[i]
            end_range = start_range

            while i + 1 < len(perimeter_distances):  # Start a new range
                if perimeter_distances[i + 1] == perimeter_distances[i] + 1:  # Check if the next index is contiguous
                    end_range = perimeter_distances[i + 1]
                    i += 1
                    continue

                next_point = self.point_from_distance(perimeter_distances[i] + 1)  # Calculate the point at the next distance

                if not rng.contains_point(next_point):  # If it's outside the rectangle, check tolerance
                    if perimeter_distances[i + 1] - perimeter_distances[i] >= segment_gap_threshold:
                        break  # Finalize the current range
                    else:
                        end_range = perimeter_distances[i + 1]  # Include the point despite being outside
                else:
                    end_range = perimeter_distances[i + 1]  # Point is inside, extend the range

                i += 1

            ranges.append((start_range, end_range))  # Finalize and store the current range
            i += 1

        return ranges

    def src(self, rng: HyperRange) -> Tuple[int, int]:
        perimeter_points = rng.boundary_points()
        perimeter_distances = sorted(self.distances_from_points(perimeter_points))

        return min(perimeter_distances), max(perimeter_distances)
