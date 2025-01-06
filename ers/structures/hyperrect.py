import functools
from itertools import product
from typing import List

from ers.util.serialization.serialization import ObjectToBytes, BytesToObject
from ers.structures.pointnd import PointND


@functools.total_ordering
class HyperRect:
    def __init__(self, start: PointND, end: PointND):
        self.start = start
        self.end = end

        if len(start.coords) != len(end.coords):
            raise ValueError("Different dimensions for start and end points")

        for i in range(0, len(start.coords)):
            if start.coords[i] > end.coords[i]:
                raise ValueError

    @classmethod
    def from_coords(cls, start: List[int], end: List[int]):
        return cls(PointND(start), PointND(end))

    def __str__(self):
        return "HyperRect[" + str(self.start) + ", " + str(self.end) + "]"

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash((self.start, self.end))

    def __eq__(self, other):
        if not isinstance(other, HyperRect):
            return False
        return self.start == other.start and self.end == other.end

    def __lt__(self, other):
        if not isinstance(other, HyperRect):
            return NotImplemented
        return self.start < other.start and self.end < other.end

    def __contains__(self, other):
        if isinstance(other, PointND):
            return self.contains_point(other)
        elif isinstance(other, HyperRect):
            return self.contains_point(other.start) and self.contains_point(other.end)
        else:
            return NotImplemented

    def to_bytes(self):
        return ObjectToBytes([self.start.coords, self.end.coords])

    @classmethod
    def from_bytes(cls, b: bytes):
        start, end = BytesToObject(b)
        return HyperRect(PointND(start), PointND(end))

    def contains_point(self, point: PointND) -> bool:
        for i in range(len(point.coords)):
            if not (self.start.coords[i] <= point.coords[i] <= self.end.coords[i]):
                return False
        return True

    def points(self) -> List[PointND]:
        dimensions = len(self.start.coords)

        ranges = [range(self.start.coords[i], self.end.coords[i] + 1) for i in range(dimensions)]

        points = []

        for p in list(product(*ranges)):
            points.append(PointND(list(p)))

        return points

    def perimeter_points(self) -> List[PointND]:
        corners = list(product(*[[self.start.coords[i], self.end.coords[i]] for i in range(len(self.start.coords))]))
        corners.sort()

        perimeter_points = []
        for c in corners:
            perimeter_points.append(PointND(list(c)))

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
                    perimeter_points.append(PointND(point[:]))

        return perimeter_points

    def volume(self) -> int:
        p = 1

        for (v1, v2) in zip(self.start.coords, self.end.coords):
            p = p * (v2 - v1)

        return p
