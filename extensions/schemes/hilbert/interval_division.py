##
## Copyright 2024 Alin-Petru Rosu and Evangelia Anna Markatou
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##    http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
##

from typing import List

from hilbertcurve.hilbertcurve import HilbertCurve

from ers.structures.point import Point
from ers.structures.rect import Rect


def _perimeter_points(rect: Rect):
    points = []
    for x in range(rect.start.x, rect.end.x + 1):
        points.append(Point(x, rect.start.y))
        points.append(Point(x, rect.end.y))

    for y in range(rect.start.y + 1, rect.end.y):
        points.append(Point(rect.start.x, y))
        points.append(Point(rect.end.x, y))

    return points

class IntervalDivision:
    def divide(self, hc: HilbertCurve, rect: Rect) -> List[List[int]]:
        pass

class MinMaxDivision(IntervalDivision):
    def divide(self, hc: HilbertCurve, rect: Rect) -> List[List[int]]:
        perimeter = _perimeter_points(rect)
        hilbert_indices = sorted(list(map(lambda p: hc.distance_from_point([p.x, p.y]), perimeter)))
        return [[hilbert_indices[0], hilbert_indices[-1]]]


class PerimeterTraversalDivision(IntervalDivision):
    def divide(self, hc: HilbertCurve, rect: Rect) -> List[List[int]]:
        perimeter = _perimeter_points(rect)
        hilbert_indices = sorted(list(map(lambda p: hc.distance_from_point([p.x, p.y]), perimeter)))
        ranges = []
        i = 0
        while i < len(hilbert_indices):
            start_range = hilbert_indices[i]
            while True:
                while i < len(hilbert_indices) - 1 and hilbert_indices[i + 1] == hilbert_indices[i] + 1:
                    i = i + 1  # walk around perimeter
                # point of turn
                [x, y] = hc.point_from_distance(hilbert_indices[i] + 1)
                if not rect.contains_point(Point(x, y)):  # if point is not in search space, close query
                    ranges.append([start_range, hilbert_indices[i]])
                    break
                else:  # else, merge query and skip
                    i = i + 1
            i = i + 1
        return ranges
