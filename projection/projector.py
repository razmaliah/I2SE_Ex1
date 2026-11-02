"""Projectors: turn a plane in a volume into a 2D image (FR-13 – FR-18).

``Projector`` is the interface. Two implementations follow the Strategy pattern:

- ``ReferenceProjector``: simple loops over the pixels. Slow, easy to check by reading.
- ``FastProjector``: the same computation on whole arrays (ALGORITHM.md, section 4).

Both return an image of the volume's type, with 0 for margin pixels and for points outside
the volume. Tests require both to return identical images (NFR-2).
"""

from abc import ABC, abstractmethod

import numpy as np

from .plane import EPS


class Projector(ABC):
    """Interface: ``project(volume, plane)`` returns the plane's image as a 2D array."""

    @abstractmethod
    def project(self, volume, plane):
        """Return an array of shape ``plane.image_shape`` and type ``volume.dtype``."""


class ReferenceProjector(Projector):
    """One pixel at a time (ALGORITHM.md, section 3)."""

    def project(self, volume, plane):
        g = plane.geometry
        data = volume.data
        image = np.zeros((g.rows, g.cols), dtype=volume.dtype)
        for y in range(g.rows):
            left, right = g.row_bounds(y)
            for x in range(g.cols):
                if not (left - EPS <= x <= right + EPS):
                    continue                                       # margin
                point = g.origin + y * g.down + x * g.across
                index = np.rint(point).astype(int)                 # nearest voxel (FR-17)
                if all(0 <= i < side for i, side in zip(index, volume.shape)):
                    image[y, x] = data[tuple(index)]               # else 0 (FR-13)
        return image


class FastProjector(Projector):
    """All pixels at once with NumPy (ALGORITHM.md, section 4)."""

    def project(self, volume, plane):
        g = plane.geometry
        padded = volume.padded
        strides = np.array(padded.strides) // padded.itemsize

        y = np.arange(g.rows, dtype=float)[:, None]               # column of row numbers
        x = np.arange(g.cols, dtype=float)[None, :]               # row of column numbers

        offset = np.zeros((g.rows, g.cols), dtype=np.intp)
        for k in range(3):                                         # one coordinate at a time
            coordinate = (g.origin[k] + y * g.down[k]) + x * g.across[k]
            index = np.rint(coordinate).astype(np.intp) + 1        # +1 for the zero border
            np.clip(index, 0, volume.shape[k] + 1, out=index)      # outside -> zero border
            offset += index * strides[k]

        left, right = g.row_bounds(y)
        in_shape = (x >= left - EPS) & (x <= right + EPS)
        offset[~in_shape] = 0                                      # corner of the zero border

        return padded.ravel()[offset]
