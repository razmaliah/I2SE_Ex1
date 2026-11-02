"""Projectors: known answers (section 2 of TESTING.md) and fast = reference (NFR-2)."""

import numpy as np
import pytest

from projection import FastProjector, Plane, ReferenceProjector, Volume

PROJECTORS = [ReferenceProjector(), FastProjector()]


def coordinate_volume(shape, dtype=np.int32):
    """Each voxel stores its own position as x·10000 + y·100 + z."""
    x, y, z = np.indices(shape)
    return Volume((x * 10000 + y * 100 + z).astype(dtype))


def decode(value):
    return value // 10000, value // 100 % 100, value % 100


# --- known answers ----------------------------------------------------------------------


@pytest.mark.parametrize("projector", PROJECTORS)
def test_axis_aligned_rectangle_equals_numpy_slice(projector):
    volume = coordinate_volume((10, 12, 8))
    k = 5
    plane = Plane.from_points([(0, 0, k), (9, 0, k), (0, 11, k), (9, 11, k)])
    image = projector.project(volume, plane)
    np.testing.assert_array_equal(image, volume.data[:, :, k])


@pytest.mark.parametrize("projector", PROJECTORS)
def test_pixels_are_one_voxel_apart(projector):
    # each pixel comes from the voxel at its own row and column (FR-14a)
    volume = coordinate_volume((20, 20, 3))
    plane = Plane.from_points([(2, 9, 1), (14, 3, 1), (2, 9, 1), (14, 15, 1)])
    image = projector.project(volume, plane)
    g = plane.geometry
    for y in range(g.rows):
        for x in range(g.cols):
            if image[y, x]:
                expected = np.rint(g.origin + y * g.down + x * g.across).astype(int)
                assert decode(image[y, x]) == tuple(expected)


@pytest.mark.parametrize("projector", PROJECTORS)
def test_triangle_shape(projector):
    volume = Volume(np.ones((30, 30, 1), dtype=np.uint8))
    image = projector.project(volume, Plane.from_points([(1, 4, 0), (5, 1, 0), (5, 7, 0)]))
    expected = np.array(
        [
            [0, 0, 0, 1, 0, 0, 0],
            [0, 0, 0, 1, 0, 0, 0],
            [0, 0, 1, 1, 1, 0, 0],
            [0, 1, 1, 1, 1, 1, 0],
            [1, 1, 1, 1, 1, 1, 1],
        ]
    )
    np.testing.assert_array_equal(image, expected)


@pytest.mark.parametrize("projector", PROJECTORS)
def test_slanted_parallelogram_stays_slanted(projector):
    volume = Volume(np.ones((30, 30, 1), dtype=np.uint8))
    image = projector.project(
        volume, Plane.from_points([(1, 1, 0), (5, 4, 0), (1, 7, 0), (5, 10, 0)])
    )
    expected = np.array(
        [
            [1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
            [0, 1, 1, 1, 1, 1, 1, 0, 0, 0],
            [0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
            [0, 0, 0, 1, 1, 1, 1, 1, 1, 0],
            [0, 0, 0, 1, 1, 1, 1, 1, 1, 1],
        ]
    )
    np.testing.assert_array_equal(image, expected)


@pytest.mark.parametrize("projector", PROJECTORS)
def test_plane_outside_the_volume_is_black(projector):
    volume = Volume(np.ones((10, 10, 10), dtype=np.uint8))
    plane = Plane.from_points([(20, 20, 20), (25, 17, 20), (25, 23, 20)])
    assert not projector.project(volume, plane).any()


@pytest.mark.parametrize("projector", PROJECTORS)
def test_plane_partly_outside_is_black_where_it_leaves(projector):
    volume = Volume(np.ones((10, 10, 3), dtype=np.uint8))
    # rectangle on z = 1 from x = -3 to 12: rows 0..2 and 13..15 are outside
    image = projector.project(
        volume, Plane.from_points([(-3, 0, 1), (12, 0, 1), (-3, 9, 1), (12, 9, 1)])
    )
    assert image.shape == (16, 10)
    assert not image[:3].any() and not image[13:].any()
    assert image[3:13].all()


@pytest.mark.parametrize("projector", PROJECTORS)
def test_signed_volume_returns_raw_values(projector):
    volume = Volume(np.full((5, 5, 5), -7, dtype=np.int16))
    image = projector.project(volume, Plane.from_points([(0, 0, 2), (4, 0, 2), (0, 4, 2), (4, 4, 2)]))
    assert image.dtype == np.int16
    assert np.all(image == -7)


@pytest.mark.parametrize("projector", PROJECTORS)
def test_tiny_volume(projector):
    volume = Volume(np.full((1, 1, 1), 9, dtype=np.uint8))
    image = projector.project(volume, Plane.from_points([(0, 0, 0), (1, -1, 0), (1, 1, 0)]))
    assert image[0, image.shape[1] // 2] == 9


# --- the fast projector gives the same images as the reference (NFR-2) -------------------


def random_isosceles(rng, center, size):
    """A random triangle, trapezoid or parallelogram around ``center``."""
    across = rng.normal(size=3)
    across /= np.linalg.norm(across)
    down = np.cross(across, rng.normal(size=3))
    down /= np.linalg.norm(down)
    height = rng.uniform(2, size)
    base = rng.uniform(2, size)
    kind = rng.integers(3)
    top = 0.0 if kind == 0 else (base if kind == 2 else rng.uniform(0.5, base))
    shift = rng.uniform(-size / 3, size / 3) if kind == 2 else 0.0   # slant of a parallelogram
    a1 = center - height / 2 * down - top / 2 * across
    a2 = a1 + top * across
    b = a1 + height * down - (base - top) / 2 * across + shift * across
    c = b + base * across
    return [a1, b, c] if kind == 0 else [a1, b, a2, c]


@pytest.mark.parametrize(
    "dtype", [np.uint8, np.uint16, np.uint32, np.int8, np.int16, np.int32]
)
def test_fast_equals_reference_on_random_planes(dtype):
    rng = np.random.default_rng(2026)
    info = np.iinfo(dtype)
    volume = Volume(rng.integers(info.min, info.max, size=(24, 20, 16), dtype=dtype, endpoint=True))
    reference, fast = ReferenceProjector(), FastProjector()
    checked = 0
    while checked < 40:
        center = rng.uniform(-8, 32, size=3)                 # inside, partly and fully outside
        plane = Plane.from_points(random_isosceles(rng, center, 30))
        np.testing.assert_array_equal(fast.project(volume, plane), reference.project(volume, plane))
        checked += 1
