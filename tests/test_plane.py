"""Planes: validation rules (FR-9) and geometry (FR-14 – FR-18)."""

import math

import numpy as np
import pytest

from projection import EPS, InvalidPlaneError, Plane, Trapezoid, Triangle

# --- valid shapes -----------------------------------------------------------------------

TRIANGLE = [(0, 0, 0), (4, -3, 0), (4, 3, 0)]                # legs 5, base 6, height 4
TRAPEZOID = [(0, -2, 0), (4, -5, 0), (0, 2, 0), (4, 5, 0)]   # legs 5, top 4, base 10
RECTANGLE = [(0, 0, 0), (3, 0, 0), (0, 6, 0), (3, 6, 0)]     # legs 3, top = base = 6
PARALLELOGRAM = [(0, 0, 0), (4, 3, 0), (0, 6, 0), (4, 9, 0)]  # slanted legs 5, top = base 6


def test_factory_picks_the_shape():
    assert isinstance(Plane.from_points(TRIANGLE), Triangle)
    assert isinstance(Plane.from_points(TRAPEZOID), Trapezoid)


@pytest.mark.parametrize("count", [0, 2, 5])
def test_factory_rejects_wrong_count(count):
    with pytest.raises(InvalidPlaneError, match="3 or 4 points"):
        Plane.from_points([(0, 0, 0)] * count)


@pytest.mark.parametrize("points", [TRIANGLE, TRAPEZOID, RECTANGLE, PARALLELOGRAM])
def test_valid_shapes_are_accepted(points):
    Plane.from_points(points)


def test_lecturer_example_trapezoids_are_valid():
    Plane.from_points([(200, 0, 0), (200, 0, 500), (200, 400, 0), (200, 400, 500)])
    Plane.from_points([(200, 50, 0), (200, 0, 500), (200, 350, 0), (200, 400, 500)])


# --- each rule of FR-9, with a plane that breaks only that rule -------------------------


@pytest.mark.parametrize(
    "points, message",
    [
        ([(0, 0, 0), (4, -3, 0), (math.inf, 3, 0)], "finite"),
        ([(0, 0, 0), (4, -3, 0), (math.nan, 3, 0)], "finite"),
        ([(0, 0, 0), (4, -3, 0), (4, 3.01, 0)], "not isosceles"),
        ([(0, 0, 0), (0, 0, 0), (0, 0, 0)], "on one line"),
        ([(0, 0, 0), (4, 3, 0), (4, 3, 0)], "on one line"),
        ([(0, 0, 0), (2, 0, 0), (-2, 0, 0)], "on one line"),
    ],
)
def test_invalid_triangles(points, message):
    with pytest.raises(InvalidPlaneError, match=message):
        Plane.from_points(points)


@pytest.mark.parametrize(
    "points, message",
    [
        ([(0, -2, 0), (4, -5, 0), (0, 2, 0), (4, 5.1, 0)], "legs are not equal"),
        ([(0, -2, 0), (4, 0, 0), (0, 2, 0), (4, 0, 0)], "same point"),
        ([(0, -2, 0), (4, -5, 0), (0, 2, 1), (4, 5, 1)], "not on one plane"),
        ([(0, 2, 0), (4, -5, 0), (0, -2, 0), (4, 5, 0)], "legs cross"),
        ([(0, -5, 0), (4, -2, 0), (0, 5, 0), (4, 2, 0)], "top is longer"),
        ([(0, 0, 0), (0, 3, 0), (0, 6, 0), (0, 9, 0)], "on one line"),
    ],
)
def test_invalid_trapezoids(points, message):
    with pytest.raises(InvalidPlaneError, match=message):
        Plane.from_points(points)


def test_top_not_parallel_with_equal_legs():
    # legs of exactly 5, but a2 is 1 voxel off the line parallel to the base
    a1, b = np.array([0.0, -2, 0]), np.array([4.0, -5, 0])
    c = np.array([4.0, 5, 0])
    a2 = c + 5 * np.array([-np.sqrt(1 - 0.2**2), -0.2, 0])   # |a2c| = 5, a2 not at x = 0 line
    with pytest.raises(InvalidPlaneError, match="not parallel"):
        Plane.from_points([a1, b, a2, c])


def test_isosceles_tolerance_is_eps():
    Plane.from_points([(0, 0, 0), (4, -3, 0), (4, 3 + EPS / 2, 0)])
    with pytest.raises(InvalidPlaneError):
        Plane.from_points([(0, 0, 0), (4, -3, 0), (4, 3 + 2 * EPS, 0)])


def test_check_size():
    plane = Plane.from_points(TRIANGLE)          # 5 x 7
    plane.check_size(7)
    with pytest.raises(InvalidPlaneError, match="larger than the maximum"):
        plane.check_size(6)


# --- geometry ---------------------------------------------------------------------------


def test_triangle_geometry():
    g = Plane.from_points(TRIANGLE).geometry
    assert g.height == pytest.approx(4)                 # true height, not the leg (FR-14a)
    assert (g.rows, g.cols) == (5, 7)
    assert g.top == pytest.approx((3, 3))
    assert g.base == pytest.approx((0, 6))
    np.testing.assert_allclose(g.origin, (0, -3, 0))
    np.testing.assert_allclose(g.across, (0, 1, 0))
    np.testing.assert_allclose(g.down, (1, 0, 0))


def test_trapezoid_geometry():
    g = Plane.from_points(TRAPEZOID).geometry
    assert (g.rows, g.cols) == (5, 11)
    assert g.top == pytest.approx((3, 7))
    assert g.base == pytest.approx((0, 10))


def test_parallelogram_keeps_its_slant():
    g = Plane.from_points(PARALLELOGRAM).geometry
    assert (g.rows, g.cols) == (5, 10)
    assert g.top == pytest.approx((0, 6))
    assert g.base == pytest.approx((3, 9))


def test_row_bounds_interpolate_between_top_and_base():
    g = Plane.from_points(TRIANGLE).geometry
    left, right = g.row_bounds(np.array([0, 2, 4]))
    np.testing.assert_allclose(left, [3, 1.5, 0])
    np.testing.assert_allclose(right, [3, 4.5, 6])
