"""
HyperRange divider interface.

Defines the abstract strategy that :class:`HyperRangeTree` uses to split a node
into children. Concrete subclasses implement uniform, mid-overlap, and
data-dependent partitioning of a HyperRange.
"""

from typing import List

from ers.structures.hyperrange import HyperRange


class HyperRangeDivider:
    """
    Abstract base class for dividing a HyperRange into smaller sub-ranges.

    This class should be subclassed to implement specific division strategies.
    """

    def divide(self, rng: HyperRange) -> List[HyperRange]:
        """
        Divides the given HyperRange into smaller sub-ranges.

        :param rng: The HyperRange to be divided.
        :return: A list of smaller HyperRanges resulting from the division.
        :raises NotImplementedError: Always; subclasses must override.
        """
        raise NotImplementedError
