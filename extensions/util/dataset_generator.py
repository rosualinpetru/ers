import csv
import gzip
import shutil
from collections import defaultdict
from typing import Dict, Tuple

import matplotlib.pyplot as plt

type RawLocationData2D = Dict[Tuple[float, float], list[bytes]]
type Dataset2D = Dict[Tuple[int, int], list[bytes]]
type Dataset3D = Dict[Tuple[int, int, int], list[bytes]]


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


def map_location_to_dataset_2d(dataset: RawLocationData2D, dimension_size: int) -> Dataset2D:
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
    grid_size = 2 ** dimension_size
    point_to_nodes = defaultdict(list)

    for (lat, lon), node_ids in dataset.items():
        x = scale(lat, min_lat, max_lat, grid_size)
        y = scale(lon, min_lon, max_lon, grid_size)
        point_to_nodes[(x, y)].extend(node_ids)

    return dict(point_to_nodes)


def plot_dataset_2d(dataset: Dataset2D):
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
# GENERATORS
################################################################################################################

# Dimension should be in [0, 15] as increasing the scale brings to difference.
def generate_cali(dimension_size: int, raw_data_file: str = '../../data/cali.txt.gz') -> Dataset2D:
    dataset = defaultdict(list)

    with gzip.open(raw_data_file, 'rt') as f_in:
        reader = csv.reader(f_in, delimiter=' ')
        for row in reader:
            if len(row) >= 3:
                node_id = int(row[0])
                latitude = float(row[1])
                longitude = float(row[2])
                dataset[(latitude, longitude)].append(bytes(str(node_id), 'utf-8'))

    return map_location_to_dataset_2d(dict(dataset), dimension_size)


# The dataset was adapted to match the same format as Cali. Precisely, a unique
# id is assigned for each check-in-time.
# Dimension should be in [0, 42] as increasing the scale brings to difference.
def generate_gowalla(dimension_size: int) -> Dataset2D:
    return generate_cali(dimension_size, '../../data/gowalla.txt.gz')


# The dataset was adapted to match the same format as Cali. Precisely, a unique
# id is assigned for each latitude-longitude pair.
# Dimension should be in [0, 14] as increasing the scale brings to difference.
def generate_spitz(dimension_size: int) -> Dataset2D:
    return generate_cali(dimension_size, '../../data/spitz.txt.gz')

def generate_nh_64() -> Dataset3D:
    raw_data_file: str = '../../data/nh_64.txt.gz'

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

    return dataset