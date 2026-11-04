"""
Integer grid points of a multi-dimensional domain.
"""

import functools
from typing import List

from ers.util.serialization import serialization


@functools.total_ordering
class Point:
    """
    An immutable point of a ``d``-dimensional integer grid.

    Points are hashable (usable as multi-map keys) and ordered by *strict
    dominance*: ``p < q`` holds only if every coordinate of ``p`` is strictly
    smaller than the corresponding coordinate of ``q``; points that are not
    comparable that way are neither smaller nor greater.
    """

    def __init__(self, coords: List[int]):
        """
        :param coords: The coordinates; copied, so later changes to the list do not affect the point.
        :raises ValueError: If ``coords`` is empty.
        """
        if len(coords) == 0:
            raise ValueError("Cannot create zero-dimensional point")
        self.__coords = list(coords)
        self.__dimensions = len(coords)

    def dimensions(self) -> int:
        """The number of coordinates."""
        return self.__dimensions

    def coords(self) -> List[int]:
        """A copy of the coordinates."""
        return self.__coords[:]

    def __eq__(self, other):
        if not isinstance(other, Point):
            return False
        return self.__dimensions == other.__dimensions and self.__coords == other.__coords

    def __lt__(self, other):
        if not isinstance(other, Point):
            return NotImplemented

        if self.__dimensions != other.__dimensions:
            return NotImplemented

        for v1, v2 in zip(self.__coords, other.__coords):
            if v1 >= v2:
                return False

        return True

    def __hash__(self):
        return hash(tuple(self.__coords))

    def __bytes__(self):
        return serialization.ObjectToBytes(self.__coords)

    def __str__(self):
        return "Point(" + str(self.__coords) + ")"

    def __repr__(self):
        return str(self)

    def __getitem__(self, index):
        return self.__coords[index]
