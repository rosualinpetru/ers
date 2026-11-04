"""
Axis-aligned ranges (hyperrectangles) of the integer grid: the queries and the
canonical ranges of every range-supporting structure.
"""

import functools
from itertools import product
from typing import List

from ers.structures.point import Point
from ers.util.serialization.serialization import BytesToObject, ObjectToBytes


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
                raise ValueError(f"Range start {start} exceeds end {end} in dimension {i}")

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
        return HyperRange.from_coords([0] * len(bits), [2**b - 1 for b in bits])

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

    def intersects(self, other: "HyperRange") -> bool:
        """
        Checks whether two ranges share at least one cell.

        :param other: Another HyperRange of the same dimensionality.
        :return: True if the ranges overlap, False otherwise.
        """
        return all(self.start[i] <= other.end[i] and other.start[i] <= self.end[i] for i in range(self.dimensions))

    def points(self) -> List[Point]:
        """
        Generates all points within the range.

        :return: A list of Point objects.
        """
        ranges = [range(self.start[i], self.end[i] + 1) for i in range(self.dimensions)]
        return [Point(list(p)) for p in product(*ranges)]

    def boundary_points(self) -> List[Point]:
        """
        Computes the boundary points of the range: every cell that has at least
        one coordinate pinned to a face of the hyperrectangle.

        In 2D this is the perimeter; in 3D it is the full surface (all six
        faces, including their interiors), and so on for higher dimensions.
        The Hilbert segment-finding algorithm relies on this set being the
        complete set of cells where the curve can enter or leave the query,
        so it must include face interiors, not just edges/corners --- otherwise
        in-range Hilbert segments are missed and searches drop true positives.

        :return: A list of Point objects on the boundary.
        """
        seen = set()
        boundary = []
        for i in range(self.dimensions):
            # Pin dimension i to each of its two faces (a single value if the
            # range is degenerate in that dimension), and sweep the rest fully.
            for face_value in {self.start[i], self.end[i]}:
                axis_ranges = [[face_value] if j == i else range(self.start[j], self.end[j] + 1) for j in range(self.dimensions)]
                for coords in product(*axis_ranges):
                    if coords not in seen:
                        seen.add(coords)
                        boundary.append(Point(list(coords)))

        return boundary

    def volume(self) -> int:
        """
        Computes the volume (number of points) of the range.

        :return: The number of points contained in the range.
        """
        p = 1
        for i in range(self.dimensions):
            p *= self.end[i] - self.start[i] + 1
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
