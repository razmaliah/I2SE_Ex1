# Algorithm

This document describes how a plane is projected to an image, and how the whole run turns a
CSV file into a video. Requirement numbers (FR-x, NFR-x) refer to the [SRS](SRS.md).

## 1. Notation

| Symbol | Meaning |
|---|---|
| `M` | The volume, of shape `(sx, sy, sz)` |
| `a1, b, a2, c` | The plane's points. Legs: `a1→b` and `a2→c`. Top: `a1→a2`. Base: `b→c` |
| `L` | Leg length, `dist(a1,b) = dist(a2,c)` |
| `T`, `B` | Top length `dist(a1,a2)` and base length `dist(b,c)`, with `T ≤ B` |
| `E` | The output image, `H` rows by `W` columns |

**One shape covers all cases.** A triangle `a, b, c` is the trapezoid `a1 = a2 = a` (`T = 0`).
A parallelogram is the trapezoid with `T = B`. From here on, one algorithm covers all three
shapes.

## 2. The idea: a grid laid on the plane

The image is a square grid of spacing 1 voxel, laid flat on the plane:

- **Columns** run along the base: unit vector `u = (c − b) / B`.
- **Rows** run down, perpendicular to the base, inside the plane: with `w = b − a1`,
  `n = (w − (w·u)·u) / h`, where `h = |w − (w·u)·u|` is the true height (distance between the
  top line and the base line).
- **Origin `O`:** the top-left corner of the shape's bounding box. Each point `q` has a position
  along the base `pos(q) = (q − a1)·u`; `O = a1 + min(pos)·u`, the minimum over the four points.

Pixel `(y, x)` is the 3D point

```
p(y, x) = O + y·n + x·u
```

Image size: `H = floor(h) + 1` rows and `W = floor(max(pos) − min(pos)) + 1` columns. The `+1`
comes from including both ends (FR-15).

**A pixel belongs to the shape** if its point is between the two legs. At row `y`, with
`t = y / h` (0 at the top, 1 at the base), the legs are at

```
left(y)  = (1 − t)·pos(a1) + t·pos(b) − min(pos)
right(y) = (1 − t)·pos(a2) + t·pos(c) − min(pos)
```

and the pixel belongs to the shape if `left(y) ≤ x ≤ right(y)` (with tolerance EPS). Other
pixels are margin and stay black (FR-19).

**Why this design.**

- *No distortion (FR-14a).* Rows and columns are both 1 voxel apart, so the image keeps the
  true proportions. The assignment's algorithm steps 1 voxel along the slanted leg instead, so
  rows are only `h / L` apart and the image is stretched vertically by `L / h`: about 15% for an
  equilateral triangle, 12% for row 1 of `lecturer_example.csv` (`L = 447`, `h = 400`), and
  without limit for a flat trapezoid.
- *True shape (FR-18).* Every row is placed where it really is, so a slanted parallelogram looks
  like a slanted parallelogram. For an isosceles triangle or trapezoid this gives exactly the
  centered rows of the assignment, without a rounding rule for odd margins.
- *Direct computation (FR-16).* Every point is computed from `y` and `x`, not by adding steps,
  so rounding errors do not accumulate.

Example (a triangle with `L = 5`, `h = 4`, `B = 6`, in a volume of ones):

```
0 0 0 1 0 0 0
0 0 0 1 0 0 0
0 0 1 1 1 0 0
0 1 1 1 1 1 0
1 1 1 1 1 1 1
```

## 3. Reference algorithm (loops)

Simple and slow; kept as the reference that the fast version is tested against (NFR-2).

```
for y in 0 .. H−1:
    for x in 0 .. W−1:
        if not (left(y) − EPS ≤ x ≤ right(y) + EPS):
            E[y][x] = 0                                   # margin
            continue
        i = round(O + y·n + x·u)                          # nearest voxel (FR-17)
        E[y][x] = M[i] if i is inside M else 0            # FR-13
```

Cost: one Python iteration per pixel. A 749 × 500 image takes about 0.45 s, about 2 FPS.

## 4. Fast algorithm (no loops)

The same computation, done on whole arrays at once with NumPy. Python runs a handful of array
operations per frame instead of one iteration per pixel.

### 4.1 Preparation, once per volume

Pad the volume with a border of one zero voxel on every side: `P = pad(M, 1)`, of shape
`(sx+2, sy+2, sz+2)`. A point outside `M` is clamped onto this border, where the value is 0.
This removes the per-pixel "is it inside?" test, which was the most expensive step.

### 4.2 Per frame

1. **Row data** (`H` values each): `left(y)` and `right(y)`.
2. **Shape mask** (`H × W`): `left(y) − EPS ≤ x ≤ right(y) + EPS`.
3. **3D point of every pixel**, one coordinate at a time:
   `p[y, x] = O + y·n + x·u`, an outer sum of a column (`y` part) and a row (`x` part).
4. **Voxel index:** round, shift by 1 for the border, and clamp to `0 .. s+1`. Every index is
   now valid, and every point outside `M` lands on a zero voxel.
5. **Flat offset:** combine the three indices into one offset into the padded volume.
   Margin pixels get offset 0, which is a corner of the zero border.
6. **Read:** `E = P.flat[offset]`, one gather for the whole image.

### 4.3 Prototype results

A first prototype (with the assignment's row spacing and centered rows) was compared with the
loop version:

- Identical images, pixel for pixel, on four test triangles.
- On a 500³ volume of 8-bit voxels, on a 2-core cloud machine:

| Plane | Image size | Loops | No loops |
|---|---|---|---|
| Diagonal plane through the cube | 749 × 500 | about 2 FPS | 124 FPS |
| Large triangle around a full slice | 1118 × 1000 | – | 49 FPS |

The speed depends on the number of pixels in the image, not on the size of the volume. The
grid of section 2 has the same cost per pixel and fewer rows. A second prototype of the grid
gave the expected shapes for a triangle, an isosceles trapezoid, a rectangle and a slanted
parallelogram. The final measurement is part of the experiment.

## 5. Validation of a plane

Done for all planes before any projection (FR-10). Checks, in order (FR-9):

1. The row has 3 or 4 points and the right number of values.
2. All values are finite numbers.
3. Triangle: `|dist(a,b) − dist(a,c)| < EPS`, and the points are not on one line
   (`|(b − a) × (c − a)| > EPS`).
4. Trapezoid: `|dist(a1,b) − dist(a2,c)| < EPS`; `B > EPS` and `h > EPS` (not flat);
   `a2` is on the plane of `a1, b, c` (distance `< EPS`); `a2` is on the line through `a1`
   parallel to the base (distance `< EPS`), so the top is parallel to the base;
   `(a2 − a1)·u ≥ −EPS`, so the top points the same way and the legs do not cross; `T ≤ B`.
   Distances, not angles, are compared with EPS, so the tolerance does not grow with the size of
   the plane.
   With equal legs and parallel sides, the shape is either an isosceles trapezoid or a
   parallelogram (`T = B`); both are valid.
5. Image size: `H` and `W` are at most twice the diagonal of the volume (FR-19a).

## 6. The whole run

```
1. Read and check the arguments.                           (file-level errors stop: FR-8)
2. Load the volume. Compute its value range for intensity mapping (FR-20). Pad it (4.1).
3. Read the CSV and validate all planes (section 5). Print all warnings (FR-10).
   Strict mode with any invalid plane, or no valid plane: stop (FR-8, FR-12).
4. Frame size = the largest H and W over the valid planes (FR-19).
5. For each plane, in CSV order:                           ← projection FPS is measured here
     valid:   project (section 4), map to 0..255, center in the frame
     invalid: black frame (FR-11)
     write the frame to the video                          ← end-to-end FPS includes this
6. Print load time, projection FPS and end-to-end FPS (FR-23).
```

**Intensity mapping (FR-20):** `out = clip((v − lo) / (hi − lo) · 255, 0, 255)`, where `lo`
and `hi` are the volume's minimum and maximum (or its percentiles). Pixels outside the volume
and margin pixels are set to 0 after mapping, so they are black also when the volume has
negative values (FR-13).
