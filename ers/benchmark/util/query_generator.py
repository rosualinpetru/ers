import math
import secrets
from typing import Tuple


################################################################################################################
# 2D
################################################################################################################

def generate_random_point_2d(bound_x: int, bound_y: int) -> Tuple[int, int]:
    return secrets.randbelow(bound_x), secrets.randbelow(bound_y)


def generate_random_query_2d(bound_x: int, bound_y: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    while True:
        p1 = generate_random_point_2d(bound_x, bound_y)
        p2 = generate_random_point_2d(bound_x, bound_y)
        if p1 <= p2 and p1[1] <= p2[1]:
            break

    return p1, p2


def generate_bucket_query_2d(bound_x: int, bound_y: int, bucket_index: int, bucket_size: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    total_area = (bound_x - 1) * (bound_y - 1)
    min_area = math.ceil((bucket_index * bucket_size) / 100.0 * total_area)
    max_area = math.floor(((bucket_index + 1) * bucket_size) / 100.0 * total_area)

    min_width = max(1, math.ceil(min_area / (bound_y - 1)))  # do not consider trivial case of queries representing a point
    max_width = min(bound_x - 1, max_area)

    while True:
        width = min_width + secrets.randbelow(max(max_width - min_width + 1, 1))

        min_height = max(1, math.ceil(min_area / width))
        max_height = min(bound_y - 1, math.floor(max_area / width))

        if 0 < width < bound_x and 0 < min_height < bound_y and 0 < max_height < bound_y:
            height = min_height + secrets.randbelow(max(max_height - min_height + 1, 1))

            area = width * height
            if min_area <= area <= max_area:
                break

    while True:
        x1_max = bound_x - width
        y1_max = bound_y - height

        x1 = secrets.randbelow(x1_max)
        y1 = secrets.randbelow(y1_max)

        x2 = x1 + width
        y2 = y1 + height

        if 0 <= x1 < bound_x and 0 <= y1 <= bound_y and 0 <= x2 < bound_x and 0 <= y2 <= bound_y:
            return (x1, y1), (x2, y2)


################################################################################################################
# 3D
################################################################################################################


def generate_random_point_3d(bound_x: int, bound_y: int, bound_z: int) -> Tuple[int, int, int]:
    return secrets.randbelow(bound_x), secrets.randbelow(bound_y), secrets.randbelow(bound_z)


def generate_random_query_3d(bound_x: int, bound_y: int, bound_z: int) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    while True:
        p1 = generate_random_point_3d(bound_x, bound_y, bound_z)
        p2 = generate_random_point_3d(bound_x, bound_y, bound_z)
        if p1[0] <= p2[0] and p1[1] <= p2[1] and p1[2] <= p2[2]:
            break

    return p1, p2


def generate_bucket_query_3d(bound_x: int, bound_y: int, bound_z: int, bucket_index: int, bucket_size: int) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    total_volume = (bound_x - 1) * (bound_y - 1) * (bound_z - 1)
    min_volume = math.ceil((bucket_index * bucket_size) / 100.0 * total_volume)
    max_volume = math.floor(((bucket_index + 1) * bucket_size) / 100.0 * total_volume)

    min_width = max(1, math.ceil(min_volume / ((bound_y - 1) * (bound_z - 1))))
    max_width = min(bound_x - 1, max_volume)

    while True:
        width = min_width + secrets.randbelow(max(max_width - min_width + 1, 1))

        min_height = max(1, math.ceil(min_volume / (width * (bound_z - 1))))
        max_height = min(bound_y - 1, math.floor(max_volume / width))

        if 0 < width < bound_x and 0 < min_height < bound_y and 0 < max_height < bound_y:
            height = min_height + secrets.randbelow(max(max_height - min_height + 1, 1))

            min_depth = max(1, math.ceil(min_volume / (width * height)))
            max_depth = min(bound_z - 1, math.floor(max_volume / (width * height)))

            if 0 < height < bound_y and 0 < min_depth < bound_z and 0 < max_depth < bound_z:
                depth = min_depth + secrets.randbelow(max(max_depth - min_depth + 1, 1))

                volume = width * height * depth
                if min_volume <= volume <= max_volume:
                    break

    while True:
        x1_max = bound_x - width
        y1_max = bound_y - height
        z1_max = bound_z - depth

        x1 = secrets.randbelow(x1_max)
        y1 = secrets.randbelow(y1_max)
        z1 = secrets.randbelow(z1_max)

        x2 = x1 + width
        y2 = y1 + height
        z2 = z1 + depth

        if 0 <= x1 < bound_x and 0 <= y1 < bound_y and 0 <= z1 < bound_z and 0 <= x2 < bound_x and 0 <= y2 < bound_y and 0 <= z2 < bound_z:
            return (x1, y1, z1), (x2, y2, z2)
