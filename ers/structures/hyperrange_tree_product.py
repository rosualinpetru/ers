from itertools import product
from typing import List, Optional

from ers.structures.hyperrange import HyperRange
from ers.structures.hyperrange_tree import HyperRangeTree
from ers.structures.point import Point
from ers.util.hyperrange.divider import HyperRangeDivider


class HyperRangeTreeProduct:
    def __init__(self, trees: List[HyperRangeTree]):
        self.trees = trees
        self.dimensions = sum([t.dimensions for t in self.trees])

    @classmethod
    def init(cls, bits: List[int], division_strategy: HyperRangeDivider):
        return cls([HyperRangeTree.init(HyperRange.from_bits([h]), division_strategy) for h in bits])

    def descend(self, point: Point) -> List[HyperRange]:
        assert point.dimensions() == self.dimensions

        descended_paths = []

        processed_dimensions = 0
        for t in self.trees:
            reduced_point = point[processed_dimensions: t.dimensions]
            descended_paths.append(t.descend(HyperRange.from_point(reduced_point)))
            processed_dimensions += t.dimensions

        result = []
        for hyperrng_product in product(*descended_paths):
            result.append(self.__product_of_hyperranges_to_hyperrange(hyperrng_product))

        return result

    def brc(self, rng: HyperRange) -> List[HyperRange]:
        assert rng.dimensions() == self.dimensions

        dimensions_covers = []

        processed_dimensions = 0
        for t in self.trees:
            reduced_start = rng.start[processed_dimensions: t.dimensions]
            reduced_end = rng.end[processed_dimensions: t.dimensions]
            reduced_rng = HyperRange.from_coords(reduced_start, reduced_end)
            dimensions_covers.append(t.brc(reduced_rng))
            processed_dimensions += t.dimensions

        cover = []
        for hyperrng_product in product(*dimensions_covers):
            cover.append(self.__product_of_hyperranges_to_hyperrange(hyperrng_product))

        return cover

    def src(self, rng: HyperRange) -> Optional[HyperRange]:

        assert rng.dimensions() == self.dimensions

        dimensions_covers = []

        processed_dimensions = 0
        for t in self.trees:
            reduced_start = rng.start[processed_dimensions: t.dimensions]
            reduced_end = rng.end[processed_dimensions: t.dimensions]
            reduced_rng = HyperRange.from_coords(reduced_start, reduced_end)
            partial_src = t.src(reduced_rng)
            if partial_src is None:
                return None

            dimensions_covers.append([partial_src])
            processed_dimensions += t.dimensions

        cover = []
        for hyperrng_product in product(*dimensions_covers):
            cover.append(self.__product_of_hyperranges_to_hyperrange(hyperrng_product))

        assert len(cover) == 1
        return cover[0]

    @staticmethod
    def __product_of_hyperranges_to_hyperrange(hyperrng_product) -> HyperRange:
        start_coords = []
        end_coords = []

        for h in hyperrng_product:
            start_coords.extend(h.start.coords())
            end_coords.extend(h.end.coords())

        return HyperRange.from_coords(start_coords, end_coords)