# Test Strategy

Goal: show that the program does what the [SRS](SRS.md) says, that it never crashes, and that it
is fast enough. Every requirement has at least one test (section 7).

Tests are written with **pytest** and run with `pytest` from the repository root. The data
files they need are generated in code (see [DATASET.md](DATASET.md), section 3), so the tests
run anywhere without downloading data.

## 1. Unit tests: one component at a time

| Component | What is checked |
|---|---|
| Volume reader | 3D volumes of every supported type are read with the right shape and values; other files are rejected (FR-1 – FR-3) |
| CSV reader | Header; 3 and 4 points; empty columns; spaces and scientific notation (`1.59e2`); CSV line numbers in messages (FR-4 – FR-7) |
| Plane validation | One test per rule of FR-9, each with a plane that breaks only that rule, and a valid plane next to it that must pass (boundary at EPS) |
| Geometry | `h`, `H`, `W`, `u`, `n` and the origin for hand-computed shapes: triangle, isosceles trapezoid, rectangle, slanted parallelogram |
| Intensity mapping | min/max and percentiles; the same value gives the same gray in every frame; signed volumes; a volume with a single value (no division by zero) (FR-20) |
| Frame assembly | Frame size from the largest plane; smaller images centered; invalid plane gives a black frame (FR-11, FR-19) |

## 2. Known-answer tests: is the image right?

On synthetic volumes whose images are known in advance:

- **Axis-aligned plane = NumPy slice.** A rectangle on `z = k` must give exactly `M[:, :, k]`
  (up to orientation). This ties the whole algorithm to a result anyone can check.
- **Coordinate volume.** Each pixel's value gives the voxel it came from. Checks that rows and
  columns are 1 voxel apart (FR-14a), that rows are in the right place (FR-18), and that rounding
  picks the nearest voxel (FR-17).
- **Shapes.** In a volume of ones: a triangle gives a symmetric triangle of ones; a slanted
  parallelogram gives a slanted parallelogram; margins are 0 (FR-14, FR-18).
- **Outside the volume.** A plane completely outside gives a black image without a warning; a
  plane partly outside gives black exactly where it leaves the volume (FR-13).

## 3. Reference comparison: is the fast version right?

The fast algorithm must give **identical** images to the simple loop version (NFR-2,
ALGORITHM.md section 3). Hundreds of random valid planes (triangles, trapezoids, parallelograms;
inside, partly outside and outside the volume) on random volumes of every voxel type. The random
seed is fixed, so any failure can be reproduced.

## 4. Edge cases and robustness

The program must never crash with an unhandled exception (NFR-3):

- Planes: degenerate (repeated points, points on one line), tiny (a few pixels), the largest
  size allowed and one pixel above it (FR-19a), values like `inf`, `nan`, `abc`.
- Volumes: the smallest sizes (1 × 1 × 1), every voxel type, a volume with a single value.
- Files: missing file, empty CSV, CSV without header, CSV where every plane is invalid, NRRD that
  is not 3D or has an unsupported type (FR-8).

## 5. End-to-end tests: the demo program

Run `Ex0.py` as the user would, on small generated files:

- One frame per CSV plane, in order, all of the same size (FR-19, FR-21).
- Invalid planes: black frames, all warnings listed with line numbers, video still written
  (FR-10, FR-11).
- `--strict` with an invalid plane: no video, all errors listed, non-zero exit code (FR-12).
- File-level errors: clear message, non-zero exit code, no video (FR-8).
- The report prints load time, projection FPS and end-to-end FPS (FR-23).

## 6. Performance measurement

The automated tests check correctness only. Speed is measured separately, with a benchmark
script, on `croissant.nrrd` (500³, `uint8`) with `croissant.csv`, and on a random 500³ volume
with planes of several sizes (including the diagonal plane and a plane covering a full slice).

- The target is a projection FPS of at least 100 (NFR-1); the assignment's minimum is 30.
- The measured numbers, the machine they were measured on, and the image sizes are reported in
  the experiment.

## 7. Demo and experiment

The demo of the assignment (`python Ex0.py file.nrrd file.csv file.mp4`) is run on:

| Volume | Planes | What to look at |
|---|---|---|
| `croissant.nrrd` | `lecturer_example.csv` | Valid planes drawn, the non-isosceles triangle black with a warning |
| `MRHead_1.nrrd` | `head.csv` | Anatomy looks right; axis-aligned frames match the slices in 3D Slicer |
| `croissant.nrrd` | `croissant.csv` | Performance on 500³; planes partly outside the volume |
| `onion`, `biscuit_cake`, `swiss_roll` | their CSVs | 8, 16 and 32 bit volumes |
| `MRHead_1.nrrd` | `demo/edge_cases.csv` (ours) | One plane per edge case of section 4 and per rule of FR-9, each with the result the SRS expects |

The videos are checked by eye against the 3D Slicer views, and the results are written in the
experiment document.

## 8. Requirements coverage

| Requirement | Tests (section) |
|---|---|
| FR-1 – FR-3 (volume) | 1 (volume reader), 4 (files, volumes) |
| FR-4 – FR-7 (CSV) | 1 (CSV reader) |
| FR-8 (file-level errors) | 4, 5 |
| FR-9, FR-10 (validation) | 1 (validation), 5 |
| FR-11, FR-12 (black frame, strict) | 1 (frame assembly), 5 |
| FR-13 (outside the volume) | 2 |
| FR-14 – FR-18 (projection) | 1 (geometry), 2, 3 |
| FR-19, FR-19a (frame size) | 1, 4 |
| FR-20 (intensity) | 1 |
| FR-21 – FR-23 (video, report) | 5 |
| NFR-1 (performance) | 6 (benchmark, reported in the experiment) |
| NFR-2 (correctness of the fast version) | 3 |
| NFR-3 (robustness) | 4 |
