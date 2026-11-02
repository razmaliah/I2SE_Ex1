"""Planes: an isosceles triangle, or an isosceles trapezoid / parallelogram (FR-6, FR-9).

Every plane is reduced to the same four corners ``a1, b, a2, c`` (legs ``a1→b`` and
``a2→c``, top ``a1→a2``, base ``b→c``). A triangle is the case ``a1 = a2``. From the
corners, a ``Geometry`` describes the image grid laid on the plane (ALGORITHM.md, section 2).
"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from .errors import InvalidPlaneError

EPS = 1e-3  # tolerance of all geometric checks (assignment Q&A)


@dataclass(frozen=True)
class Geometry:
    """The image grid of a plane: pixel ``(y, x)`` is the point ``origin + y·down + x·across``."""

    origin: np.ndarray   # 3D point of pixel (0, 0): top-left corner of the bounding box
    across: np.ndarray   # unit vector along the base (columns)
    down: np.ndarray     # unit vector perpendicular to the base, toward it (rows)
    height: float        # true height h: distance between the top and the base lines
    rows: int            # H
    cols: int            # W
    top: tuple           # (left, right) column positions of the top, a1 and a2
    base: tuple          # (left, right) column positions of the base, b and c

    def row_bounds(self, y):
        """Left and right edges (column positions) of row(s) ``y``; works on arrays."""
        t = np.minimum(np.asarray(y, dtype=float) / self.height, 1.0)
        left = (1 - t) * self.top[0] + t * self.base[0]
        right = (1 - t) * self.top[1] + t * self.base[1]
        return left, right


class Plane(ABC):
    """A plane given by 3 or 4 points. Created through ``Plane.from_points``.

    The constructor validates the points (FR-9) and computes the geometry, so an existing
    ``Plane`` object is always valid.
    """

    point_count = None  # set by each subclass

    def __init__(self, points):
        points = np.asarray(points, dtype=float)
        if points.shape != (self.point_count, 3):
            raise InvalidPlaneError(
                f"{type(self).__name__.lower()} needs {self.point_count} points of 3 numbers"
            )
        if not np.all(np.isfinite(points)):
            raise InvalidPlaneError("all coordinates must be finite numbers")
        self._points = points
        self._validate()
        self._geometry = _build_geometry(*self.corners())

    @staticmethod
    def from_points(points):
        """Create a ``Triangle`` (3 points) or a ``Trapezoid`` (4 points)."""
        count = len(points)
        if count == 3:
            return Triangle(points)
        if count == 4:
            return Trapezoid(points)
        raise InvalidPlaneError(f"a plane needs 3 or 4 points, not {count}")

    @property
    def points(self):
        return self._points.copy()

    @property
    def geometry(self):
        return self._geometry

    @property
    def image_shape(self):
        """``(H, W)`` of the plane's image."""
        return self._geometry.rows, self._geometry.cols

    def check_size(self, max_side):
        """Reject an image larger than ``max_side`` in either direction (FR-19a)."""
        rows, cols = self.image_shape
        if rows > max_side or cols > max_side:
            raise InvalidPlaneError(
                f"image of {rows} x {cols} pixels is larger than the maximum "
                f"of {max_side:.0f} (twice the volume diagonal)"
            )

    @abstractmethod
    def _validate(self):
        """Raise ``InvalidPlaneError`` if the points break a rule of this shape."""

    @abstractmethod
    def corners(self):
        """The four corners ``(a1, b, a2, c)``."""

    def __repr__(self):
        points = ", ".join(str(tuple(np.round(p, 3))) for p in self._points)
        return f"{type(self).__name__}({points})"


class Triangle(Plane):
    """An isosceles triangle ``a, b, c``: apex ``a``, base ``b→c``."""

    point_count = 3

    def _validate(self):
        a, b, c = self._points
        ab, ac = _dist(a, b), _dist(a, c)
        if abs(ab - ac) >= EPS:
            raise InvalidPlaneError(f"triangle is not isosceles: |ab|={ab:.4f}, |ac|={ac:.4f}")
        if np.linalg.norm(np.cross(b - a, c - a)) <= EPS:
            raise InvalidPlaneError("the triangle's points are on one line")

    def corners(self):
        a, b, c = self._points
        return a, b, a, c


class Trapezoid(Plane):
    """An isosceles trapezoid or a parallelogram ``a1, b, a2, c`` (legs ``a1→b``, ``a2→c``)."""

    point_count = 4

    def _validate(self):
        a1, b, a2, c = self._points
        leg1, leg2 = _dist(a1, b), _dist(a2, c)
        top, base = _dist(a1, a2), _dist(b, c)
        if abs(leg1 - leg2) >= EPS:
            raise InvalidPlaneError(f"legs are not equal: |a1b|={leg1:.4f}, |a2c|={leg2:.4f}")
        if base <= EPS:
            raise InvalidPlaneError("b and c are the same point")
        across = (c - b) / base
        if _off_line(b - a1, across) <= EPS:
            raise InvalidPlaneError("the top and the base are on one line")
        normal = np.cross(b - a1, c - a1)
        normal /= np.linalg.norm(normal)
        if abs(np.dot(a2 - a1, normal)) >= EPS:
            raise InvalidPlaneError("the four points are not on one plane")
        if _off_line(a2 - a1, across) >= EPS:
            raise InvalidPlaneError("the top is not parallel to the base")
        if np.dot(a2 - a1, across) < -EPS:
            raise InvalidPlaneError("the legs cross (a1 and a2 are swapped)")
        if top > base + EPS:
            raise InvalidPlaneError(
                f"the top is longer than the base: |a1a2|={top:.4f}, |bc|={base:.4f}"
            )

    def corners(self):
        return tuple(self._points)


def _dist(p, q):
    return float(np.linalg.norm(q - p))


def _off_line(w, direction):
    """Distance of vector ``w`` from the line along the unit vector ``direction``."""
    return float(np.linalg.norm(w - np.dot(w, direction) * direction))


def _build_geometry(a1, b, a2, c):
    across = (c - b) / _dist(b, c)
    w = b - a1
    perpendicular = w - np.dot(w, across) * across
    height = float(np.linalg.norm(perpendicular))
    down = perpendicular / height

    position = [float(np.dot(p - a1, across)) for p in (a1, b, a2, c)]
    left_most = min(position)
    origin = a1 + left_most * across
    position = [p - left_most for p in position]

    return Geometry(
        origin=origin,
        across=across,
        down=down,
        height=height,
        rows=math.floor(height + EPS) + 1,
        cols=math.floor(max(position) + EPS) + 1,
        top=(position[0], position[2]),
        base=(position[1], position[3]),
    )
