from itertools import product
from typing import List

from ers.structures.hyperrange import HyperRange
from ers.structures.hypertree import HyperTree
from ers.structures.point import Point


class RangeTreeMD:
    def __init__(self, heights: List[int]):
        self.trees = [HyperTree.initialize_tree(h, 1) for h in heights]
        self.dimensions = len(heights)

    def parents_of(self, point: Point) -> List[HyperRange]:
        assert point.dimensions() == self.dimensions

        parents = []

        descended_paths = [self.trees[d].rng.descend(Point([point[d]])) for d in range(self.dimensions)]

        # all are of dimension 1
        for hyperrng_product in product(*descended_paths):
            parents.append(self.__product_of_hyperranges_to_hyperrange(hyperrng_product))

        return parents

    def generate_cover(self, rng: HyperRange) -> List[HyperRange]:
        cover = []

        dimensions_covers = [self.trees[d].get_brc_range_cover(HyperRange.from_coords([rng.start[d]], [rng.end[d]])) for d in range(self.dimensions)]

        # all are of dimension 1
        for hyperrng_product in product(*dimensions_covers):
            cover.append(self.__product_of_hyperranges_to_hyperrange(hyperrng_product))

        return cover

    @staticmethod
    def __product_of_hyperranges_to_hyperrange(hyperrng_product) -> HyperRange:
        start_coords = []
        end_coords = []

        for h in hyperrng_product:
            start_coords.append(h.start[0])
            end_coords.append(h.end[0])

        return HyperRange.from_coords(start_coords, end_coords)
