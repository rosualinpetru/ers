from itertools import product
from typing import List, Optional

from ers.structures.hyperrange import HyperRange
from ers.structures.hyperrange_tree import HyperRangeTree
from ers.structures.point import Point


class HyperRangeTreeProduct:
    """
    Represents a product of multiple HyperRangeTree instances.

    This class provides methods for initializing a product tree, descending through the structure,
    and computing best range covering (BRC) and single region covering (SRC) for a given range.
    """

    def __init__(self, trees: List[HyperRangeTree]):
        """
        Initializes a HyperRangeTreeProduct instance.

        :param trees: List of HyperRangeTree instances representing independent dimensions.
        """
        self.trees = trees
        self.dimensions = sum([t.dimensions for t in self.trees])

    def descend(self, point: Point) -> List[HyperRange]:
        """
        Finds all HyperRanges containing the given point in the product space.

        :param point: A Point in the multi-dimensional space.
        :return: A list of HyperRanges covering the point.
        """
        assert point.dimensions() == self.dimensions

        descended_paths = []
        processed_dimensions = 0
        for t in self.trees:
            reduced_point = point[processed_dimensions: processed_dimensions + t.dimensions]
            descended_paths.append(t.descend(HyperRange.from_point_coords(reduced_point)))
            processed_dimensions += t.dimensions

        return [self.__product_of_hyperranges_to_hyperrange(p) for p in product(*descended_paths)]

    def brc(self, rng: HyperRange) -> List[HyperRange]:
        """
        Computes the best range covering (BRC) of the given range as
        the product of BRC of each tree.

        :param rng: The HyperRange to cover.
        :return: A list of HyperRanges forming the BRC.
        """
        assert rng.dimensions == self.dimensions

        dimensions_covers = []
        processed_dimensions = 0
        for t in self.trees:
            reduced_start = rng.start[processed_dimensions: processed_dimensions + t.dimensions]
            reduced_end = rng.end[processed_dimensions:processed_dimensions + t.dimensions]
            reduced_rng = HyperRange.from_coords(reduced_start, reduced_end)
            dimensions_covers.append(t.brc(reduced_rng))
            processed_dimensions += t.dimensions

        return [self.__product_of_hyperranges_to_hyperrange(p) for p in product(*dimensions_covers)]

    def src(self, rng: HyperRange) -> Optional[HyperRange]:
        """
        Finds the single range covering (SRC) the given range as the product of
        SRC of each tree.

        :param rng: The HyperRange to cover.
        :return: The single HyperRange covering the given range or None if no coverage is found.
        """
        assert rng.dimensions == self.dimensions

        dimensions_covers = []
        processed_dimensions = 0
        for t in self.trees:
            reduced_start = rng.start[processed_dimensions: processed_dimensions + t.dimensions]
            reduced_end = rng.end[processed_dimensions: processed_dimensions + t.dimensions]
            reduced_rng = HyperRange.from_coords(reduced_start, reduced_end)
            partial_src = t.src(reduced_rng)
            if partial_src is None:
                return None
            dimensions_covers.append([partial_src])
            processed_dimensions += t.dimensions

        cover = [self.__product_of_hyperranges_to_hyperrange(p) for p in product(*dimensions_covers)]
        assert len(cover) == 1
        return cover[0]

    @staticmethod
    def __product_of_hyperranges_to_hyperrange(hyperrng_product) -> HyperRange:
        """
        Constructs a single HyperRange by combining multiple independent HyperRanges.

        :param hyperrng_product: A tuple of HyperRanges from different dimensions.
        :return: A combined HyperRange.
        """
        start_coords = []
        end_coords = []
        for h in hyperrng_product:
            start_coords.extend(h.start.coords())
            end_coords.extend(h.end.coords())
        return HyperRange.from_coords(start_coords, end_coords)
