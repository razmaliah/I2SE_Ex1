"""The 3D volume (FR-1 – FR-3)."""

import math

import numpy as np

from .errors import InputError

MAX_SIDE = 1023  # sizes are 1 .. 2^10 - 1 (FR-3)
SUPPORTED_TYPES = (np.uint8, np.uint16, np.uint32, np.int8, np.int16, np.int32)  # FR-2


class Volume:
    """A 3D matrix of integer voxels, ``data[x, y, z]``.

    The volume is checked once, when it is created. It also keeps a copy padded with one
    zero voxel on every side, which the fast projector uses so that a point outside the
    volume needs no special test (ALGORITHM.md, section 4.1).
    """

    def __init__(self, data):
        data = np.asarray(data)
        if data.ndim != 3:
            raise InputError(f"the volume must be 3D, but it has {data.ndim} dimensions")
        if data.dtype.type not in SUPPORTED_TYPES:
            raise InputError(
                f"voxel type {data.dtype} is not supported; "
                "use 8, 16 or 32 bit integers (signed or unsigned)"
            )
        if not all(1 <= side <= MAX_SIDE for side in data.shape):
            raise InputError(
                f"volume size {data.shape} is out of range; "
                f"each side must be 1 .. {MAX_SIDE}"
            )
        self._data = np.ascontiguousarray(data)
        self._padded = None

    @property
    def data(self):
        """The voxels, as a read-only view."""
        view = self._data.view()
        view.flags.writeable = False
        return view

    @property
    def shape(self):
        return self._data.shape

    @property
    def dtype(self):
        return self._data.dtype

    @property
    def diagonal(self):
        """Length of the volume's diagonal, in voxels."""
        return math.sqrt(sum(side * side for side in self.shape))

    @property
    def padded(self):
        """The volume with one zero voxel around it, created on first use."""
        if self._padded is None:
            self._padded = np.pad(self._data, 1)
        return self._padded

    def value_range(self, low_percentile=None, high_percentile=None):
        """The range ``(lo, hi)`` used for intensity mapping (FR-20).

        Without percentiles: the minimum and the maximum of the volume.
        """
        if low_percentile is None and high_percentile is None:
            return self._data.min().item(), self._data.max().item()
        lo, hi = np.percentile(self._data, [low_percentile or 0, high_percentile or 100])
        return float(lo), float(hi)

    def __repr__(self):
        return f"Volume(shape={self.shape}, dtype={self.dtype})"
