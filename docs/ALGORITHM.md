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

**A triangle is a trapezoid whose top is a single point.** A triangle `a, b, c` is handled as
the trapezoid `a1 = a2 = a` (so `T = 0`). From here on, one algorithm covers both shapes.

## 2. Geometry

Walking down both legs at the same speed, the two walkers are always on a line parallel to the
base (that is what makes the trapezoid isosceles). Each such line is one row of the image.

- Leg directions (unit vectors): `v1 = (b − a1) / L`, `v2 = (c − a2) / L`.
- Row direction (unit vector, the same for all rows): `u = (c − b) / B`.
- True height (distance between the top and the base lines):
  `h = |w − (w·u)·u|`, where `w = b − a1`.
- **Row spacing.** Row `y` is `y` voxels below the top, measured perpendicular to the base. To
  get there, each walker moves `y·s` along its leg, where `s = L / h` (FR-14a).
- Row `y` (`y = 0` at the top) runs from `p1(y) = a1 + y·s·v1` to `p2(y) = a2 + y·s·v2` (FR-16).
- Its length is `d(y) = dist(p1(y), p2(y))`, growing linearly from `T` to `B`.
- Image size: `H = floor(h) + 1` rows, `W = floor(B) + 1` columns. The `+1` comes from including
  both end points (FR-15).

**Why not `H = L` as in the assignment.** Stepping 1 voxel along a slanted leg moves the row
only `h / L < 1` voxel down, while pixels in a row are 1 voxel apart. The image would be
stretched vertically by `L / h`: about 15% for an equilateral triangle, 12% for row 1 of
`lecturer_example.csv` (`L = 447`, `h = 400`), and without limit as the trapezoid gets flat.
With `s = L / h` rows and columns are both 1 voxel apart, so the image keeps the true proportions.

## 3. Reference algorithm (loops)

This is the assignment's algorithm with the decisions of the SRS, including the true row
spacing `s`. It is simple and slow, and it
is kept as the reference that the fast version is tested against (NFR-2).

```
for y in 0 .. H−1:
    p1 = a1 + y·s·v1
    p2 = a2 + y·s·v2
    d  = dist(p1, p2)
    n  = floor(d) + 1                  # samples in this row (FR-15)
    start = (W − n) // 2               # center the row; odd margins go right (FR-18)
    for k in 0 .. n−1:
        p = p1 + k·u
        i = round(p)                   # nearest voxel (FR-17)
        E[y][start + k] = M[i] if i is inside M else 0      # FR-13
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

1. **Row data** (`H` values each): `p1(y)`, `d(y)`, `n(y) = floor(d(y)) + 1`,
   `start(y) = (W − n(y)) // 2`.
2. **Step index of every pixel** (`H × W`): `k[y, x] = x − start(y)`. A pixel belongs to its row
   if `0 ≤ k < n(y)`; otherwise it is a margin pixel.
3. **3D point of every pixel**, one coordinate at a time: `p[y, x] = p1(y) + k[y, x]·u`.
   Because `u` is the same for all rows, this is one multiply and one add per coordinate.
4. **Voxel index:** round, shift by 1 for the border, and clamp to `0 .. s+1`. Every index is
   now valid, and every point outside `M` lands on a zero voxel.
5. **Flat offset:** combine the three indices into one offset into the padded volume.
   Margin pixels get offset 0, which is a corner of the zero border.
6. **Read:** `E = P.flat[offset]`, one gather for the whole image.

### 4.3 Correctness and speed of the prototype

A prototype of this algorithm was compared with the reference algorithm (section 3):

- Identical images, pixel for pixel, on four test triangles.
- On a 500³ volume of 8-bit voxels, on a 2-core cloud machine:

| Plane | Image size | Loops (section 3) | No loops (section 4) |
|---|---|---|---|
| Diagonal plane through the cube | 749 × 500 | about 2 FPS | 124 FPS |
| Large triangle around a full slice | 1118 × 1000 | – | 49 FPS |

The speed depends on the number of pixels in the image, not on the size of the volume. The
prototype used the assignment's row spacing (`H = L`); with the true height (FR-14a) images have
fewer rows, so they are at least as fast. The final measurement is part of the experiment.

## 5. Validation of a plane

Done for all planes before any projection (FR-10). Checks, in order (FR-9):

1. The row has 3 or 4 points and the right number of values.
2. All values are finite numbers.
3. Triangle: `|dist(a,b) − dist(a,c)| < EPS`, and the points are not on one line
   (`|(b − a) × (c − a)| > EPS`).
4. Trapezoid: `|dist(a1,b) − dist(a2,c)| < EPS`; `T ≤ B`; `a2` is on the plane of `a1, b, c`
   (distance `< EPS`); the top is parallel to the base and points the same way
   (`(a2 − a1)/T · u > 1 − EPS`), so the legs do not cross.
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
and `hi` are the volume's minimum and maximum (or its percentiles). Pixels outside the volume are
set to 0 after mapping, so they are black also when the volume has negative values (FR-13).
