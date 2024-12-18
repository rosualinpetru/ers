import math
import secrets
from typing import Dict, Tuple, List

type RawLocationData2D = Dict[Tuple[float, float], List[bytes]]
type Dataset2D = Dict[Tuple[int, int], List[bytes]]
type Dataset3D = Dict[Tuple[int, int, int], List[bytes]]


################################################################################################################
# 2D
################################################################################################################

def generate_random_point_2d(bound_x: int, bound_y: int) -> Tuple[int, int]:
    return secrets.randbelow(bound_x), secrets.randbelow(bound_y)


def generate_random_query_2d(bound_x: int, bound_y: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    while True:
        p1 = generate_random_point_2d(bound_x, bound_y)
        p2 = generate_random_point_2d(bound_x, bound_y)
        if p1 < p2:
            break

    return p1, p2


def generate_bucket_query_2d(bound_x: int, bound_y: int, bucket_index: int, bucket_size: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    total_area = bound_x * bound_y
    min_area = math.ceil((bucket_index * bucket_size) / 100.0 * total_area)
    max_area = math.floor(((bucket_index + 1) * bucket_size) / 100.0 * total_area)

    while True:
        w = secrets.randbelow(bound_x) + 1

        h_min = math.ceil(min_area / w)
        h_max = math.floor(max_area / w)

        if h_min > h_max:
            continue

        max_x_1 = bound_x - w - 1
        max_y_1 = bound_y - h_min - 1

        if max_x_1 < 0 or max_y_1 < 0:
            continue

        x_1 = secrets.randbelow(max_x_1 + 1)
        y_1 = secrets.randbelow(max_y_1 + 1)
        p1 = (x_1, y_1)

        actual_h_max = min(h_max, bound_y - y_1 - 1)
        if actual_h_max < h_min:
            continue

        h = secrets.randbelow(actual_h_max - h_min + 1) + h_min
        p2 = (p1[0] + w, p1[1] + h)

        return p1, p2


################################################################################################################
# 3D
################################################################################################################


def generate_random_point_3d(bound_x: int, bound_y: int, bound_z: int) -> Tuple[int, int, int]:
    return secrets.randbelow(bound_x), secrets.randbelow(bound_y), secrets.randbelow(bound_z)


def generate_random_query_3d(bound_x: int, bound_y: int, bound_z: int) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    while True:
        p1 = generate_random_point_3d(bound_x, bound_y, bound_z)
        p2 = generate_random_point_3d(bound_x, bound_y, bound_z)
        if p1 < p2:
            break

    return p1, p2


def generate_bucket_query_3d(bound_x: int, bound_y: int, bound_z: int, bucket_index: int, bucket_size: int) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    total_volume = bound_x * bound_y * bound_z
    min_volume = math.ceil((bucket_index * bucket_size) / 100.0 * total_volume)
    max_volume = math.floor(((bucket_index + 1) * bucket_size) / 100.0 * total_volume)

    while True:
        w_x = secrets.randbelow(bound_x) + 1
        w_y = secrets.randbelow(bound_y) + 1

        denom = w_x * w_y
        w_z_min = math.ceil(min_volume / denom)
        w_z_max = math.floor(max_volume / denom)

        if w_z_min > w_z_max:
            continue

        max_x_1 = bound_x - w_x
        max_y_1 = bound_y - w_y
        max_z_1 = bound_z - w_z_min

        if max_x_1 < 0 or max_y_1 < 0 or max_z_1 < 0:
            continue

        x_1 = secrets.randbelow(max_x_1 + 1)
        y_1 = secrets.randbelow(max_y_1 + 1)
        z_1 = secrets.randbelow(max_z_1 + 1)
        p1 = (x_1, y_1, z_1)

        actual_w_z_max = min(w_z_max, bound_z - z_1)

        if actual_w_z_max < w_z_min:
            continue

        w_z = secrets.randbelow(actual_w_z_max - w_z_min + 1) + w_z_min

        p2 = (p1[0] + w_x, p1[1] + w_y, p1[2] + w_z)

        return p1, p2
