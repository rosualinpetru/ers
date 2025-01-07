import functools
from itertools import product
from typing import List

from ers.util.serialization.serialization import ObjectToBytes, BytesToObject
from ers.structures.point import Point


@functools.total_ordering
class HyperRange:
    def __init__(self, start: Point, end: Point):
        self.start = start
        self.end = end

        if start.dimensions() != end.dimensions():
            raise ValueError("Different dimensions for start and end points")

        self.dimensions = start.dimensions()

        for i in range(0, start.dimensions()):
            if start[i] > end[i]:
                raise ValueError

    @classmethod
    def from_coords(cls, start: List[int], end: List[int]):
        return cls(Point(start), Point(end))

    def __str__(self):
        return "HyperRect[" + str(self.start) + ", " + str(self.end) + "]"

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash((self.start, self.end))

    def __bytes__(self):
        return ObjectToBytes([self.start.coords(), self.end.coords()])

    def __eq__(self, other):
        if not isinstance(other, HyperRange):
            return False
        return self.start == other.start and self.end == other.end

    def __lt__(self, other):
        if not isinstance(other, HyperRange):
            return NotImplemented
        return self.start < other.start and self.end < other.end

    def __contains__(self, other):
        if isinstance(other, Point):
            return self.contains_point(other)
        elif isinstance(other, HyperRange):
            return self.contains_point(other.start) and self.contains_point(other.end)
        else:
            return NotImplemented

    def to_bytes(self) -> bytes:
        return bytes(self)

    @classmethod
    def from_bytes(cls, b: bytes) -> "HyperRange":
        start, end = BytesToObject(b)
        return HyperRange(Point(start), Point(end))

    def contains_point(self, point: Point) -> bool:
        for i in range(self.dimensions):
            if not (self.start[i] <= point[i] <= self.end[i]):
                return False
        return True

    def points(self) -> List[Point]:
        ranges = [range(self.start[i], self.end[i] + 1) for i in range(self.dimensions)]

        points = []

        for p in list(product(*ranges)):
            points.append(Point(list(p)))

        return points

    def boundary_points(self) -> List[Point]:
        corners = list(product(*[[self.start[i], self.end[i]] for i in range(self.dimensions)]))
        corners.sort()

        perimeter_points = []
        for c in corners:
            perimeter_points.append(Point(list(c)))

        for i in range(len(corners)):
            for j in range(i + 1, len(corners)):
                diff_index = None
                diffs = 0
                for idx, (v1, v2) in enumerate(zip(corners[i], corners[j])):
                    if v1 != v2:
                        diff_index = idx
                        diffs += 1

                if diffs != 1:
                    continue

                point = list(corners[i][:])
                for new_v in range(corners[i][diff_index] + 1, corners[j][diff_index]):
                    point[diff_index] = new_v
                    perimeter_points.append(Point(point[:]))

        return perimeter_points

    def volume(self) -> int:
        p = 1

        for i in range(self.dimensions):
            p = p * (self.end[i] - self.start[i])

        return p

    def divide(self) -> List["HyperRange"]:
        def helper(rng: HyperRange, current_dim: int):
            if current_dim >= rng.dimensions:
                return [rng]

            midpoint = (rng.start[current_dim] + rng.end[current_dim]) // 2

            if rng.end[current_dim] - rng.start[current_dim] < 1:
                return helper(rng, current_dim + 1)

            start_coords1 = rng.start.coords()
            end_coords1 = rng.end.coords()

            start_coords2 = rng.start.coords()
            end_coords2 = rng.end.coords()

            end_coords1[current_dim] = midpoint
            start_coords2[current_dim] = midpoint + 1

            rng1 = HyperRange.from_coords(start_coords1, end_coords1)
            rng2 = HyperRange.from_coords(start_coords2, end_coords2)

            divided_rngs1 = helper(rng1, current_dim + 1)
            divided_rngs2 = helper(rng2, current_dim + 1)

            return divided_rngs1 + divided_rngs2

        return helper(self, 0)

    def descend(self, point: Point) -> List["HyperRange"]:
        assert point.dimensions() == self.dimensions

        ranges = []

        rng = self
        while rng != HyperRange(point, point):
            ranges.append(rng)
            for c in rng.divide():
                if point in c:
                    rng = c
                    break

        ranges.append(HyperRange(point, point))
        return ranges
