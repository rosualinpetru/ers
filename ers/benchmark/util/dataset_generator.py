"""
Dataset generators for the benchmarks.

Loads the real-world location datasets (Cali, Gowalla, Spitz, NH) from the
gzipped files under ``data/`` and normalises them onto an integer grid, and
provides synthetic dense/random generators. Every generator returns a multi-map
from integer coordinate tuples to lists of record-id byte strings.
"""

import csv
import gzip
import itertools
import secrets
import shutil
from collections import defaultdict
from typing import Dict, List, Tuple


################################################################################################################
# UTILS
################################################################################################################
def compute_max_dimension(generator):
    """
    Finds the smallest domain size beyond which a generator stops gaining resolution.

    Increments the domain size until enlarging it no longer changes the number of
    distinct grid cells produced -- i.e. the point at which finer scaling adds no
    further distinguishable points.

    :param generator: A callable mapping a domain size to a dataset dict.
    :return: The domain size at which the distinct-cell count stabilises.
    """
    i = 0
    while True:
        if len(generator(i).values()) == len(generator(i + 1).values()):
            return i

        i = i + 1


def compress_file(input_file: str, output_file: str):
    """
    Gzip-compresses a file.

    :param input_file: Path to the raw input file.
    :param output_file: Path to the gzipped output file to create.
    """
    with open(input_file, "rb") as f_in:
        with gzip.open(output_file, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


def map_location_to_dataset_2d(dataset: Dict[Tuple[float, float], List[bytes]], domain_size: int) -> Dict[Tuple[int, int], List[bytes]]:
    """
    Normalises floating-point (lat, lon) keys onto an integer grid of the given size.

    Each coordinate is min-max scaled into ``[0, 2**domain_size - 1]``; points that
    collide on the same grid cell have their record lists merged.

    :param dataset: A multi-map keyed by (latitude, longitude) float pairs.
    :param domain_size: The bit-length of each grid dimension.
    :return: A multi-map keyed by integer (x, y) grid cells.
    """
    # Extract latitudes and longitudes from the dataset keys
    latitudes = [point[0] for point in dataset.keys()]
    longitudes = [point[1] for point in dataset.keys()]

    # Find the min and max values for normalization
    min_lat, max_lat = min(latitudes), max(latitudes)
    min_lon, max_lon = min(longitudes), max(longitudes)

    # Define the scaling function
    def scale(value, min_val, max_val, scale_max):
        normalized = (value - min_val) / (max_val - min_val)
        return round(normalized * (scale_max - 1))

    # Map each point and store collisions in a dictionary
    grid_size = 2**domain_size
    point_to_nodes = defaultdict(list)

    for (lat, lon), node_ids in dataset.items():
        x = scale(lat, min_lat, max_lat, grid_size)
        y = scale(lon, min_lon, max_lon, grid_size)
        point_to_nodes[(x, y)].extend(node_ids)

    return dict(point_to_nodes)


def plot_dataset_2d(dataset: Dict[Tuple[int, int], List[bytes]]):
    """
    Renders a log-density hexbin plot of a 2D dataset's point distribution.

    :param dataset: A multi-map keyed by integer (x, y) grid cells.
    """
    import matplotlib.pyplot as plt  # only needed for this plotting helper

    x_coords = [point[0] for point in dataset.keys()]
    y_coords = [point[1] for point in dataset.keys()]

    plt.figure(figsize=(10, 8))
    plt.hexbin(x_coords, y_coords, gridsize=200, cmap="viridis", bins="log")
    plt.colorbar(label="Log Density")
    plt.title("Mapped Points Density in Domain Space")
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")
    plt.grid(True, alpha=0.3)
    plt.show()


################################################################################################################
# GENERATORS - Datasets 2D
################################################################################################################


# Dimension should be in [0, 15] as increasing the scale beyond brings no difference.
def generate_cali(domain_size: int, records_limit: int, raw_data_file: str = "./data/cali.txt.gz") -> Dict[Tuple[int, int], List[bytes]]:
    """
    Loads a Cali-format ``(id, lat, lon)`` dataset and maps it onto an integer grid.

    Records are uniformly subsampled to at most ``records_limit`` before being
    projected onto a ``2**domain_size`` grid via :func:`map_location_to_dataset_2d`.

    :param domain_size: The bit-length of each grid dimension.
    :param records_limit: The maximum number of raw records to keep.
    :param raw_data_file: Path to the gzipped whitespace-separated data file.
    :return: A multi-map keyed by integer (x, y) grid cells.
    """
    all_records = []

    with gzip.open(raw_data_file, "rt") as f_in:
        reader = csv.reader(f_in, delimiter=" ")

        for row in reader:
            if len(row) >= 3:
                node_id = int(row[0])
                latitude = float(row[1])
                longitude = float(row[2])

                all_records.append((latitude, longitude, node_id))

    dataset = defaultdict(list)

    if len(all_records) > records_limit:
        step = len(all_records) // records_limit
        all_records = [record for i, record in enumerate(all_records) if i % step == 0]

    for latitude, longitude, node_id in all_records:
        dataset[(latitude, longitude)].append(bytes(str(node_id), "utf-8"))

    return map_location_to_dataset_2d(dict(dataset), domain_size)


# The dataset was adapted to match the same format as Cali. Precisely, a unique
# id is assigned for each check-in-time.
# Dimension should be in [0, 42] as increasing the scale beyond brings no difference.
def generate_gowalla(domain_size: int, records_limit: int) -> Dict[Tuple[int, int], List[bytes]]:
    """
    Loads the Gowalla check-in dataset (Cali file format) onto an integer grid.

    :param domain_size: The bit-length of each grid dimension.
    :param records_limit: The maximum number of raw records to keep.
    :return: A multi-map keyed by integer (x, y) grid cells.
    """
    return generate_cali(domain_size, records_limit, "./data/gowalla.txt.gz")


# The dataset was adapted to match the same format as Cali. Precisely, a unique
# id is assigned for each latitude-longitude pair.
# Dimension should be in [0, 14] as increasing the scale beyond brings no difference.
def generate_spitz(domain_size: int, records_limit: int) -> Dict[Tuple[int, int], List[bytes]]:
    """
    Loads the Spitz location dataset (Cali file format) onto an integer grid.

    :param domain_size: The bit-length of each grid dimension.
    :param records_limit: The maximum number of raw records to keep.
    :return: A multi-map keyed by integer (x, y) grid cells.
    """
    return generate_cali(domain_size, records_limit, "./data/spitz.txt.gz")


################################################################################################################
# GENERATORS - Datasets 3D
################################################################################################################


def generate_nh_64() -> Dict[Tuple[int, int, int], List[bytes]]:
    """
    Loads the 3D NH dataset of ``(id, x, y, z)`` records already on a 64-wide grid.

    Coordinates are used as-is (no rescaling), so this generator takes no domain
    or records-limit parameters. They are parsed as integers: index labels are
    serialized coordinates, so a float ``2.0`` and an int ``2`` would be
    different labels and queries (always integer) would miss every record.

    :return: A multi-map keyed by integer (x, y, z) grid cells.
    """
    raw_data_file: str = "./data/nh_64.txt.gz"

    dataset = defaultdict(list)

    with gzip.open(raw_data_file, "rt") as f_in:
        reader = csv.reader(f_in, delimiter=" ")
        for row in reader:
            if len(row) >= 4:
                node_id = int(row[0])
                x = int(float(row[1]))
                y = int(float(row[2]))
                z = int(float(row[3]))
                dataset[(x, y, z)].append(bytes(str(node_id), "utf-8"))

    return dict(dataset)


################################################################################################################
# GENERATORS - Programmatic
################################################################################################################


def generate_dense_database_2d(domain_size: int, records_limit: int) -> Dict[Tuple[int, int], List[bytes]]:
    """
    Generates a synthetic 2D dataset by evenly sampling the full grid.

    Walks the grid in row-major order and keeps every ``step``-th cell so the
    (up to ``records_limit``) points are spread uniformly across the domain.

    :param domain_size: The bit-length of each grid dimension.
    :param records_limit: The maximum number of points to generate.
    :return: A multi-map keyed by integer (x, y) grid cells.
    """
    if records_limit <= 0:
        return {}

    max_possible_records = (2**domain_size) * (2**domain_size)
    if records_limit >= max_possible_records:
        step = 1
    else:
        step = max_possible_records // records_limit

    dataset = defaultdict(list)
    i = 0
    count = 0
    for x, y in itertools.product(range(2**domain_size), range(2**domain_size)):
        if i % step == 0:
            dataset[(x, y)].append(bytes(str([x, y]), "utf-8"))
            count += 1
            if count >= records_limit:
                break
        i += 1

    return dict(dataset)


def generate_dense_database_3d(domain_size: int, records_limit: int) -> Dict[Tuple[int, int, int], List[bytes]]:
    """
    Generates a synthetic 3D dataset by evenly sampling the grid.

    Analogous to :func:`generate_dense_database_2d` but over a 3D grid; keeps every
    ``step``-th cell in row-major order up to ``records_limit`` points.

    :param domain_size: The bit-length of each grid dimension.
    :param records_limit: The maximum number of points to generate.
    :return: A multi-map keyed by integer (x, y, z) grid cells.
    """
    if records_limit <= 0:
        return {}

    max_possible_records = (2**domain_size) * (2**domain_size)
    if records_limit >= max_possible_records:
        step = 1
    else:
        step = max_possible_records // records_limit

    dataset = defaultdict(list)
    i = 0
    count = 0
    for x, y, z in itertools.product(range(2**domain_size), range(2**domain_size), range(2**domain_size)):
        if i % step == 0:
            dataset[(x, y, z)].append(bytes(str([x, y, z]), "utf-8"))
            count += 1
            if count >= records_limit:
                break
        i += 1

    return dict(dataset)


def generate_random_database_2d(domain_size: int, records_limit: int) -> Dict[Tuple[int, int], List[bytes]]:
    """
    Generates a synthetic 2D dataset of uniformly random points.

    Draws ``records_limit`` points uniformly at random from the grid; colliding
    points accumulate under the same cell.

    :param domain_size: The bit-length of each grid dimension.
    :param records_limit: The number of random points to generate.
    :return: A multi-map keyed by integer (x, y) grid cells.
    """
    dataset = defaultdict(list)
    i = 1

    for index in range(records_limit):
        (x, y) = secrets.randbelow(2**domain_size), secrets.randbelow(2**domain_size)
        dataset[(x, y)].append(bytes(str(i), "utf-8"))
        i = i + 1

    return dict(dataset)
