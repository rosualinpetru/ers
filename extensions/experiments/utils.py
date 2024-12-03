import random
from typing import Dict, List

from ers.structures.point import Point
from ers.util.serialization import ObjectToBytes


def random_plaintext_mm(number_of_files: int, space_start: Point, space_end: Point) -> Dict[Point, List[bytes]]:
    plaintext_mm = {}
    for i in range(number_of_files):
        x = random.randint(space_start.x, space_end.x)
        y = random.randint(space_start.y, space_end.y)
        k = Point(x, y)
        c = ObjectToBytes(f'({x}, {y})')

        if k in plaintext_mm:
            l = plaintext_mm.get(k)
            l.append(c)
            plaintext_mm.update({k: l})
        else:
            plaintext_mm.update({k: [c]})

    return plaintext_mm


def fill_space_plaintext_mm(space_start: Point, space_end: Point) -> Dict[Point, List[bytes]]:
    plaintext_mm = {}
    for y in range(space_start.y, space_end.y + 1):
        for x in range(space_start.x, space_end.x + 1):
            k = Point(x, y)
            c = ObjectToBytes(f'({x}, {y})')
            plaintext_mm.update({k: [c]})
    return plaintext_mm


def generate_all_queries_2d(space_start: Point, space_end: Point) -> List[tuple[Point, Point]]:
    queries = []

    for x1 in range(space_start.x, space_end.x):
        for y1 in range(space_start.y, space_end.y):
            for x2 in range(x1 + 1, space_end.x + 1):
                for y2 in range(y1 + 1, space_end.y + 1):
                    queries.append((Point(x1, y1), Point(x2, y2)))

    return queries


def random_query_2d(space_start: Point, space_end: Point) -> tuple[Point, Point]:
    while True:
        query_start = Point(random.randint(space_start.x, space_end.x), random.randint(space_start.x, space_end.x))
        query_end = Point(random.randint(space_start.x, space_end.x), random.randint(space_start.x, space_end.x))

        if query_start < query_end:
            break

    return query_start, query_end
