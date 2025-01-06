import functools
from typing import List

from ers.util import serialization


@functools.total_ordering
class PointND:
    def __init__(self, coords: List[int]):
        self.coords = coords

    def __eq__(self, other):
        if not isinstance(other, PointND):
            return False
        return self.coords == other.coords

    def __lt__(self, other):
        if not isinstance(other, PointND):
            return NotImplemented

        if len(self.coords) != len(other.coords):
            return NotImplemented

        for v1, v2 in zip(self.coords, other.coords):
            if v1 >= v2:
                return False

        return True

    def __hash__(self):
        return hash(tuple(self.coords))

    def __bytes__(self):
        return serialization.ObjectToBytes(self.coords)

    def __str__(self):
        return "PointND(" + str(self.coords) + ")"

    def __repr__(self):
        return str(self)

    def __getitem__(self, index):
        return self.coords[index]
