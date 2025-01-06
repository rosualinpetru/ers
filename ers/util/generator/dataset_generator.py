import csv
import gzip
import itertools
import secrets
import shutil
from collections import defaultdict
from typing import Dict, Tuple, List

import matplotlib.pyplot as plt


################################################################################################################
# UTILS
################################################################################################################
def compute_max_dimension(generator):
    i = 0
    while True:
        if len(generator(i).values()) == len(generator(i + 1).values()):
            return i

        i = i + 1


def compress_file(input_file: str, output_file: str):
    with open(input_file, 'rb') as f_in:
        with gzip.open(output_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)


def map_location_to_dataset_2d(dataset: Dict[Tuple[float, float], List[bytes]], dimension_bits: int) -> Dict[Tuple[int, int], List[bytes]]:
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
    grid_size = 2 ** dimension_bits
    point_to_nodes = defaultdict(list)

    for (lat, lon), node_ids in dataset.items():
        x = scale(lat, min_lat, max_lat, grid_size)
        y = scale(lon, min_lon, max_lon, grid_size)
        point_to_nodes[(x, y)].extend(node_ids)

    return dict(point_to_nodes)


def plot_dataset_2d(dataset: Dict[Tuple[int, int], List[bytes]]):
    x_coords = [point[0] for point in dataset.keys()]
    y_coords = [point[1] for point in dataset.keys()]

    plt.figure(figsize=(10, 8))
    plt.hexbin(x_coords, y_coords, gridsize=200, cmap='viridis', bins='log')
    plt.colorbar(label='Log Density')
    plt.title("Mapped Points Density in Domain Space")
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")
    plt.grid(True, alpha=0.3)
    plt.show()


################################################################################################################
# GENERATORS - Datasets 2D
################################################################################################################

# Dimension should be in [0, 15] as increasing the scale beyond brings no difference.
def generate_cali(dimension_bits: int, records_limit: int, raw_data_file: str = './data/cali.txt.gz') -> Dict[Tuple[int, int], List[bytes]]:
    all_records = []

    with gzip.open(raw_data_file, 'rt') as f_in:
        reader = csv.reader(f_in, delimiter=' ')

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
        dataset[(latitude, longitude)].append(bytes(str(node_id), 'utf-8'))

    return map_location_to_dataset_2d(dict(dataset), dimension_bits)


# The dataset was adapted to match the same format as Cali. Precisely, a unique
# id is assigned for each check-in-time.
# Dimension should be in [0, 42] as increasing the scale beyond brings no difference.
def generate_gowalla(dimension_bits: int, records_limit: int) -> Dict[Tuple[int, int], List[bytes]]:
    return generate_cali(dimension_bits, records_limit, './data/gowalla.txt.gz')


# The dataset was adapted to match the same format as Cali. Precisely, a unique
# id is assigned for each latitude-longitude pair.
# Dimension should be in [0, 14] as increasing the scale beyond brings no difference.
def generate_spitz(dimension_bits: int, records_limit: int) -> Dict[Tuple[int, int], List[bytes]]:
    return generate_cali(dimension_bits, records_limit, './data/spitz.txt.gz')


################################################################################################################
# GENERATORS - Datasets 3D
################################################################################################################

def generate_nh_64() -> Dict[Tuple[int, int, int], List[bytes]]:
    raw_data_file: str = './data/nh_64.txt.gz'

    dataset = defaultdict(list)

    with gzip.open(raw_data_file, 'rt') as f_in:
        reader = csv.reader(f_in, delimiter=' ')
        for row in reader:
            if len(row) >= 4:
                node_id = int(row[0])
                x = float(row[1])
                y = float(row[2])
                z = float(row[3])
                dataset[(x, y, z)].append(bytes(str(node_id), 'utf-8'))

    return dict(dataset)


################################################################################################################
# GENERATORS - Programmatic
################################################################################################################

def generate_dense_database_2d(dimension_bits: int, records_limit: int) -> Dict[Tuple[int, int], List[bytes]]:
    if records_limit <= 0:
        return {}

    max_possible_records = (2 ** dimension_bits) * (2 ** dimension_bits)
    if records_limit >= max_possible_records:
        step = 1
    else:
        step = max_possible_records // records_limit

    dataset = defaultdict(list)
    i = 0
    count = 0
    for x, y in itertools.product(range(2 ** dimension_bits), range(2 ** dimension_bits)):
        if i % step == 0:
            dataset[(x, y)].append(bytes(str(i), 'utf-8'))
            count += 1
            if count >= records_limit:
                break
        i += 1

    return dict(dataset)


def generate_random_database_2d(dimension_bits: int, records_limit: int) -> Dict[Tuple[int, int], List[bytes]]:
    dataset = defaultdict(list)
    i = 1

    for index in range(records_limit):
        (x, y) = secrets.randbelow(2 ** dimension_bits), secrets.randbelow(2 ** dimension_bits)
        dataset[(x, y)].append(bytes(str(i), 'utf-8'))
        i = i + 1

    return dict(dataset)
