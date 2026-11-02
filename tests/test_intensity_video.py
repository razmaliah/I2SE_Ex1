"""Intensity mapping (FR-20) and video building (FR-19, FR-21, FR-22)."""

import imageio.v3 as iio
import numpy as np
import pytest

from projection import FastProjector, Plane, Volume
from projection.intensity import IntensityMapper
from projection.video import VideoWriter, frame_shape, place

# --- intensity --------------------------------------------------------------------------


def test_min_max_mapping():
    volume = Volume(np.array([0, 500, 1000], dtype=np.uint16).reshape(3, 1, 1))
    mapped = IntensityMapper().map(volume)
    assert mapped.dtype == np.uint8
    np.testing.assert_allclose(mapped.data.ravel(), [0, 127.5, 255], atol=0.5)


def test_signed_values():
    volume = Volume(np.array([-100, 0, 100], dtype=np.int16).reshape(3, 1, 1))
    np.testing.assert_allclose(IntensityMapper().map(volume).data.ravel(), [0, 127.5, 255], atol=0.5)


def test_outside_is_black_for_negative_values():
    # every voxel is negative; after mapping, the zero border (outside) is still black
    volume = Volume(np.full((4, 4, 4), -50, dtype=np.int16))
    volume_with_range = Volume(np.concatenate([volume.data, np.full((1, 4, 4), -10, np.int16)]))
    mapped = IntensityMapper().map(volume_with_range)
    plane = Plane.from_points([(-5, 0, 1), (8, 0, 1), (-5, 3, 1), (8, 3, 1)])
    image = FastProjector().project(mapped, plane)
    assert not image[:5].any()          # rows outside the volume


def test_percentiles_clip_extreme_values():
    data = np.zeros((100, 1, 1), dtype=np.uint32)
    data[:, 0, 0] = np.arange(100)
    data[99] = 1_000_000                 # one extreme voxel
    plain = IntensityMapper().map(Volume(data)).data.ravel()
    clipped = IntensityMapper(1, 98).map(Volume(data)).data.ravel()
    assert plain[50] == 0                # the extreme voxel makes everything else dark
    assert 100 < clipped[50] < 160
    assert clipped[99] == 255


def test_same_value_same_gray_everywhere():
    data = np.random.default_rng(1).integers(0, 4000, (30, 30, 30), dtype=np.uint16)
    data[3, 4, 5] = data[20, 21, 22] = 1234
    mapped = IntensityMapper().map(Volume(data)).data
    assert mapped[3, 4, 5] == mapped[20, 21, 22]


def test_single_value_volume():
    mapped = IntensityMapper().map(Volume(np.full((3, 3, 3), 7, dtype=np.uint8)))
    assert np.all(mapped.data == 255)


@pytest.mark.parametrize("low, high", [(1, None), (50, 10), (-1, 50), (10, 101)])
def test_bad_percentiles(low, high):
    with pytest.raises(ValueError):
        IntensityMapper(low, high)


# --- frames and video -------------------------------------------------------------------


def test_frame_shape_is_largest_and_even():
    assert frame_shape([(5, 7), (9, 3), (2, 2)]) == (10, 8)


def test_place_centers_the_image():
    frame = place(np.full((2, 3), 9, dtype=np.uint8), (6, 7))
    assert frame.shape == (6, 7)
    np.testing.assert_array_equal(np.argwhere(frame), [[2, 2], [2, 3], [2, 4], [3, 2], [3, 3], [3, 4]])


def test_video_has_every_frame_in_order(tmp_path):
    path = tmp_path / "out.mp4"
    shape = (32, 48)
    levels = [0, 80, 160, 240]
    with VideoWriter(path, shape, fps=10) as writer:
        for level in levels:
            writer.write(np.full(shape, level, dtype=np.uint8))
    frames = iio.imread(path)
    assert frames.shape[:3] == (4, 32, 48)
    means = frames[..., 0].reshape(4, -1).mean(axis=1)
    np.testing.assert_allclose(means, levels, atol=3)       # lossy compression


def test_video_rejects_wrong_frame(tmp_path):
    with VideoWriter(tmp_path / "out.mp4", (8, 8), fps=10) as writer:
        with pytest.raises(ValueError):
            writer.write(np.zeros((8, 10), dtype=np.uint8))
        writer.write(np.zeros((8, 8), dtype=np.uint8))
