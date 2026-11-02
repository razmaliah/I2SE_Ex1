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

        # Work arrays are reused and filled in place, so each pixel costs few memory passes.
        # int32 is enough for offsets: the padded volume has at most 1025³ < 2³¹ voxels.
        shape = (g.rows, g.cols)
        coordinate = np.empty(shape)
        index = np.empty(shape, dtype=np.int32)
        offset = np.zeros(shape, dtype=np.int32)
        for k in range(3):                                         # one coordinate at a time
            np.multiply(x, g.across[k], out=coordinate)
            coordinate += g.origin[k] + y * g.down[k]              # origin + y·down + x·across
            np.rint(coordinate, out=coordinate)                    # nearest voxel (FR-17)
            np.clip(coordinate, -1, volume.shape[k], out=coordinate)   # outside -> border
            index[...] = coordinate
            index += 1                                             # +1 for the zero border
            index *= int(strides[k])
            offset += index

        left, right = g.row_bounds(y)
        offset[(x < left - EPS) | (x > right + EPS)] = 0           # margin: corner of the border

        return padded.ravel()[offset]
