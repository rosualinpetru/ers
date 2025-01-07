from typing import List, Tuple

from ers.structures.hyperrange import HyperRange


class Scaler:
    def __init__(self, bits: int):
        self.bits = bits

    def downscale(self, bits: int, query: HyperRange) -> HyperRange:
        p1 = query.start.coords()
        p2 = query.end.coords()

        if bits > 0:
            def downscale_point(p: List[int]):
                for k, val in enumerate(p):
                    half = val // 2
                    p[k] = half + (val % half) if half != 0 else 0

                return p

            for _ in range(bits):
                p1 = downscale_point(p1)
                p2 = downscale_point(p2)

            reduced_max_coordinate = 1 << (self.bits - bits)

            # extend query by 1 on each dimension
            for i, v in enumerate(p1):
                p1[i] = max(0, v - 1)

            for i, v in enumerate(p2):
                p2[i] = min(reduced_max_coordinate, v + 1)

        return HyperRange.from_coords(p1, p2)

    @staticmethod
    def _hilbert_upscale(bits: int, ranges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        upscale_factor = bits * 2
        upscaled_ranges = []

        for rng in ranges:
            start_curve_point = rng[0] << upscale_factor
            end_curve_point = rng[1] << upscale_factor

            upscaled_ranges.append((start_curve_point, end_curve_point))

        return upscaled_ranges
