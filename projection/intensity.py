"""Intensity mapping: voxel values to gray levels 0..255 (FR-20)."""

import numpy as np

from .volume import Volume

CHUNK = 16  # x-slices mapped at a time, to keep memory low on large 32 bit volumes


class IntensityMapper:
    """Maps a whole volume to 8 bit once, before any projection.

    One linear range ``lo → 0, hi → 255`` is used for the whole video, so the same value
    has the same gray in every frame. With nearest-voxel sampling, mapping the volume first
    gives exactly the same pixels as mapping every frame, and it is done only once.
    The mapped volume's zero border also makes everything outside the volume black, even
    when the original values are negative (FR-13).
    """

    def __init__(self, low_percentile=None, high_percentile=None):
        if (low_percentile is None) != (high_percentile is None):
            raise ValueError("give both percentiles or neither")
        if low_percentile is not None and not 0 <= low_percentile < high_percentile <= 100:
            raise ValueError("percentiles must satisfy 0 <= low < high <= 100")
        self.low_percentile = low_percentile
        self.high_percentile = high_percentile

    def map(self, volume):
        """Return a new ``Volume`` of type ``uint8``."""
        lo, hi = volume.value_range(self.low_percentile, self.high_percentile)
        source = volume.data
        out = np.empty(volume.shape, dtype=np.uint8)
        if hi <= lo:                       # a single value: show it as white
            out.fill(255)
            return Volume(out)
        scale = 255.0 / (hi - lo)
        for start in range(0, volume.shape[0], CHUNK):
            part = source[start:start + CHUNK].astype(np.float64)
            part -= lo
            part *= scale
            np.clip(part, 0, 255, out=part)
            out[start:start + CHUNK] = np.rint(part)
        return Volume(out)
