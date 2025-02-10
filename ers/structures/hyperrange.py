import functools
from itertools import product
from typing import List

from ers.structures.point import Point
from ers.util.serialization.serialization import ObjectToBytes, BytesToObject


@functools.total_ordering
class HyperRange:
    """
    Represents a multi-dimensional range (hyperrectangle) defined by a start and end point.

    This class provides methods to construct hyperranges from different inputs, check containment,
    retrieve boundary points, compute volume, and serialize/deserialize the object.
    """

    def __init__(self, start: Point, end: Point):
        """
        Initializes a HyperRange with a start and end point.

        :param start: The starting point of the range.
        :param end: The ending point of the range.
        :raises ValueError: If the points have different dimensions or if start > end in any dimension.
        """
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
        """
        Creates a HyperRange from coordinate lists.

        :param start: List of integers representing the start coordinates.
        :param end: List of integers representing the end coordinates.
        :return: A HyperRange instance.
        """
        return cls(Point(start[:]), Point(end[:]))

    @classmethod
    def from_point(cls, p: Point):
        """
        Creates a HyperRange where both start and end points are the same.

        :param p: A Point object.
        :return: A HyperRange instance.
        """
        return cls(Point(p.coords()), Point(p.coords()))

    @classmethod
    def from_point_coords(cls, coords: List[int]):
        """
        Creates a HyperRange from a list of coordinates, treating them as both start and end.

        :param coords: List of coordinates.
        :return: A HyperRange instance.
        """
        return cls(Point(coords[:]), Point(coords[:]))

    @classmethod
    def from_bits(cls, bits: List[int]):
        """
        Creates a HyperRange from a list of bit lengths.

        :param bits: List of integers representing bit lengths.
        :return: A HyperRange instance.
        """
        return HyperRange.from_coords([0] * len(bits), [2 ** b - 1 for b in bits])

    @classmethod
    def from_bytes(cls, b: bytes):
        """
        Deserializes a HyperRange from bytes.

        :param b: Byte representation of a HyperRange.
        :return: A HyperRange instance.
        """
        start, end = BytesToObject(b)
        return HyperRange(Point(start), Point(end))

    def to_bytes(self) -> bytes:
        """
        Serializes the HyperRange to bytes.

        :return: Byte representation of the HyperRange.
        """
        return bytes(self)

    def contains_point(self, point: Point) -> bool:
        """
        Checks whether a given point is inside the range.

        :param point: A Point object.
        :return: True if the point is within the range, False otherwise.
        """
        for i in range(self.dimensions):
            if not (self.start[i] <= point[i] <= self.end[i]):
                return False
        return True

    def points(self) -> List[Point]:
        """
        Generates all points within the range.

        :return: A list of Point objects.
        """
        ranges = [range(self.start[i], self.end[i] + 1) for i in range(self.dimensions)]
        return [Point(list(p)) for p in product(*ranges)]

    def boundary_points(self) -> List[Point]:
        """
        Computes the boundary points of the range.

        :return: A list of Point objects on the boundary.
        """
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
        """
        Computes the volume (number of points) of the range.

        :return: The number of points contained in the range.
        """
        p = 1
        for i in range(self.dimensions):
            p *= (self.end[i] - self.start[i] + 1)
        return p

    def __str__(self):
        return "[(" + ", ".join([str(c) for c in self.start.coords()]) + "), (" + ", ".join([str(c) for c in self.end.coords()]) + ")]"

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
        """
        Checks whether a point or another HyperRange is contained within this range.

        :param other: A Point or HyperRange instance.
        :return: True if the point or range is contained, False otherwise.
        """
        if isinstance(other, Point):
            return self.contains_point(other)
        elif isinstance(other, HyperRange):
            return self.contains_point(other.start) and self.contains_point(other.end)
        else:
            return NotImplemented
