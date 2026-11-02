"""Volume: accepted and rejected inputs (FR-1 – FR-3)."""

import numpy as np
import pytest

from projection import InputError, Volume


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16, np.uint32, np.int8, np.int16, np.int32])
def test_accepts_every_supported_type(dtype):
    volume = Volume(np.zeros((2, 3, 4), dtype=dtype))
    assert volume.shape == (2, 3, 4)
    assert volume.dtype == dtype


@pytest.mark.parametrize("dtype", [np.float32, np.float64, np.int64, np.uint64, bool])
def test_rejects_unsupported_type(dtype):
    with pytest.raises(InputError, match="not supported"):
        Volume(np.zeros((2, 2, 2), dtype=dtype))


@pytest.mark.parametrize("shape", [(5, 5), (2, 2, 2, 2)])
def test_rejects_non_3d(shape):
    with pytest.raises(InputError, match="3D"):
        Volume(np.zeros(shape, dtype=np.uint8))


@pytest.mark.parametrize("shape", [(0, 4, 4), (1024, 1, 1)])
def test_rejects_size_out_of_range(shape):
    with pytest.raises(InputError, match="out of range"):
        Volume(np.zeros(shape, dtype=np.uint8))


def test_smallest_and_largest_sizes():
    assert Volume(np.zeros((1, 1, 1), dtype=np.uint8)).shape == (1, 1, 1)
    assert Volume(np.zeros((1023, 1, 1), dtype=np.uint8)).shape == (1023, 1, 1)


def test_data_is_read_only():
    volume = Volume(np.zeros((2, 2, 2), dtype=np.uint8))
    with pytest.raises(ValueError):
        volume.data[0, 0, 0] = 1


def test_padded_has_zero_border():
    volume = Volume(np.full((2, 3, 4), 7, dtype=np.int16))
    padded = volume.padded
    assert padded.shape == (4, 5, 6)
    assert np.all(padded[1:-1, 1:-1, 1:-1] == 7)
    assert padded.sum() == 7 * 2 * 3 * 4


def test_value_range():
    data = np.arange(-50, 50, dtype=np.int16).reshape(4, 5, 5)
    volume = Volume(data)
    assert volume.value_range() == (-50, 49)
    lo, hi = volume.value_range(1, 99)
    assert -50 < lo < hi < 49


def test_diagonal():
    assert Volume(np.zeros((3, 4, 12), dtype=np.uint8)).diagonal == pytest.approx(13)
