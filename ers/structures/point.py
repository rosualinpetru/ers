import functools
from typing import List

from ers.util.serialization import serialization


@functools.total_ordering
class Point:
    def __init__(self, coords: List[int]):
        self.__coords = coords
        self.__dimensions = len(coords)

        if len(self.__coords) == 0:
            raise ValueError("Cannot create zero-dimensional point")

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

    def dimensions(self):
        return self.__dimensions

    def coords(self):
        return self.__coords[:]
