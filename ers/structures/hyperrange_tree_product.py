from itertools import product
from typing import List, Optional, Tuple

from ers.structures.hyperrange import HyperRange
from ers.structures.hyperrange_tree import HyperRangeTree


class HyperRangeTreeProduct:
    """
    Represents a product of multiple HyperRangeTree instances: the
    multi-dimensional range tree (or TDAG) of Falzon et al., whose nodes are
    tuples of per-dimension nodes.

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

    def descend(self, rng: HyperRange) -> List[HyperRange]:
        """
        Finds all product nodes containing the given range: the product of the
        per-dimension root-to-leaf paths of its projections.

        :param rng: A HyperRange in the product space (typically a single point).
        :return: A list of HyperRanges containing ``rng``.
        """
        assert rng.dimensions == self.dimensions

        descended_paths = []
        for t, reduced_rng in self.__project(rng):
            descended_paths.append(t.descend(reduced_rng))

        return [self.__product_of_hyperranges_to_hyperrange(p) for p in product(*descended_paths)]

    def __project(self, rng: HyperRange) -> List[Tuple[HyperRangeTree, HyperRange]]:
        """Pairs every tree with the projection of ``rng`` onto that tree's dimensions."""
        projections = []
        processed_dimensions = 0
        for t in self.trees:
            reduced_start = rng.start[processed_dimensions : processed_dimensions + t.dimensions]
            reduced_end = rng.end[processed_dimensions : processed_dimensions + t.dimensions]
            projections.append((t, HyperRange.from_coords(reduced_start, reduced_end)))
            processed_dimensions += t.dimensions
        return projections

    def brc(self, rng: HyperRange) -> List[HyperRange]:
        """
        Computes the best range covering (BRC) of the given range as
        the product of BRC of each tree.

        :param rng: The HyperRange to cover.
        :return: A list of HyperRanges forming the BRC.
        """
        assert rng.dimensions == self.dimensions

        dimensions_covers = [t.brc(reduced_rng) for t, reduced_rng in self.__project(rng)]

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
        for t, reduced_rng in self.__project(rng):
            partial_src = t.src(reduced_rng)
            if partial_src is None:
                return None
            dimensions_covers.append([partial_src])

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
