# Software Requirements Specification – Plane Projection

## 1. Introduction

### 1.1 Purpose

This document defines what the program must do. The assignment leaves many details open; each
such detail is decided here, with the reason for the decision.

### 1.2 Definitions

| Term | Meaning |
|---|---|
| Volume | The 3D matrix `M[x][y][z]` read from the NRRD file |
| Voxel | One entry of the volume |
| Plane | One CSV row: an isosceles triangle (3 points) or an isosceles trapezoid (4 points) |
| Frame | The 2D image of one plane, one frame of the output video |
| EPS | Tolerance for geometric checks, `0.001` |

## 2. Input

### 2.1 Volume (NRRD)

- **FR-1** The program reads a 3D volume from an NRRD file.
- **FR-2** Supported voxel types: 8, 16 and 32 bit integers, unsigned and signed.
  - *Reason:* the assignment states unsigned values, but the MRI file it recommends
    (`MRHead_1.nrrd`) is `short` (signed 16 bit). Signed values need no special handling, since
    intensity mapping (FR-20) uses the actual range of the volume.
- **FR-3** Supported sizes: `1 ≤ sx, sy, sz < 1024`.

### 2.2 Planes (CSV)

- **FR-4** The first line is a header: `Number of Points (3 or 4),x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4`.
- **FR-5** Each following line is one plane. It starts with the number of points, 3 or 4,
  followed by the coordinates. For a triangle the last three columns are empty.
- **FR-6** Point order:
  - Triangle: `a, b, c`, where `a` is the apex and `b→c` is the base.
  - Trapezoid: `a1, b, a2, c`, where the legs are `a1→b` and `a2→c`, `a1→a2` is the top and
    `b→c` is the base.
  - *Reason:* the points are listed leg by leg: each leg is given by its two end points, one
    after the other. The lecturer's example (`lecturer_example.csv`) follows this order.
- **FR-7** Coordinates are voxel indices, as real numbers. They may be outside the volume.
  - *Reason:* this is what the assignment's algorithm assumes, and it is simpler.
  - *Limitation:* NRRD voxels are not always cubes (e.g. 1 × 1 × 1.3 mm). For such volumes the
    image is stretched along the longer voxel axis. Conversion to millimeters is a possible
    extension.

## 3. Validation

### 3.1 File-level errors – the program stops

- **FR-8** The program stops with a clear message and a non-zero exit code, and writes no
  video, if:
  - an input file does not exist or cannot be read;
  - the NRRD file is not a valid 3D volume of a supported type (FR-2, FR-3);
  - the CSV file has no header or no planes;
  - all planes are invalid.

### 3.2 Plane-level errors

- **FR-9** A plane is invalid if any of the following holds:
  1. The number of points is not 3 or 4, or the number of values does not match it.
  2. A value is not a finite number.
  3. Triangle: `|dist(a,b) − dist(a,c)| ≥ EPS` (not isosceles).
  4. Triangle: the points are on one line, or two of them are the same point.
  5. Trapezoid: `|dist(a1,b) − dist(a2,c)| ≥ EPS` (legs not equal).
  6. Trapezoid: `dist(a1,a2) > dist(b,c)` (top longer than base).
  7. Trapezoid: the four points are not on one plane (distance of `a2` from the plane of
     `a1, b, c` is `≥ EPS`).
  8. Trapezoid: the top is not parallel to the base, or the legs cross (the top and the base
     point in opposite directions). Equal legs alone do not make an isosceles trapezoid.
  9. The image of the plane is larger than the maximum frame size (FR-19a).
  - *Note on item 6:* the algorithm itself would work with a top longer than the base (the image
    would narrow toward the bottom). The plane is rejected because the assignment's definition
    requires `dist(a1,a2) ≤ dist(b,c)`.
- **FR-10** All planes are validated **before** any projection, and all errors are reported
  together, with their CSV line numbers. Example:
  `2 of 30 planes are invalid: line 4: triangle is not isosceles (|ab|=497.39, |ac|=476.86); line 8: value 'abc' is not a number`.
- **FR-11** Default mode: an invalid plane produces a **black frame**, the warning is printed and
  the run continues.
  - *Reason:* frame N in the video always matches plane N in the CSV. Skipping a plane would
    shift all following frames.
  - *Reason for rejecting non-isosceles triangles instead of drawing them:* the algorithm steps
    the same number of times on both legs. With unequal legs one side does not reach its end
    point or passes it, and the rows are not parallel to the base, so the image does not show
    the requested plane.
- **FR-12** Strict mode (`--strict`): if any plane is invalid, the program prints all errors and
  stops before projecting. No video is written.

### 3.3 Not an error

- **FR-13** A valid plane that is partly or completely outside the volume is not an error. The
  parts outside the volume are black (output value 0, also for volumes with negative values).
  No warning is printed.

## 4. Projection

- **FR-14** Each valid plane is projected row by row, from the apex (`a`, or the top `a1→a2`)
  to the base. Each row is parallel to the base and runs between the two legs.
- **FR-14a** The image is not distorted: rows are 1 voxel apart, measured perpendicular to the
  base, and samples in a row are 1 voxel apart. So the image height is the trapezoid's true
  height `h`, not the leg length.
  - *Reason:* the assignment's algorithm steps 1 voxel along the leg. Since the leg is slanted,
    rows end up less than 1 voxel apart and the image is stretched vertically by `L / h`
    (about 12% for row 1 of `lecturer_example.csv`, and without limit for a flat trapezoid).
    The assignment's algorithm is an example, not a requirement; an undistorted image is what
    the user needs.
- **FR-15** Both end points of every row are included (`x1 ≤ d12`), so a row of length `d` has
  `floor(d) + 1` samples.
- **FR-16** The points of row `y` on the legs are computed directly from `y`, not by adding
  steps, so rounding errors do not accumulate.
- **FR-17** Sampling uses the **nearest voxel** (rounding each coordinate).
  - *Reason:* speed, and the image shows only values that were actually measured.
    Interpolation creates values that were never measured.
- **FR-18** Each row is centered horizontally. When it cannot be centered exactly, it is shifted
  half a pixel to the left.

## 5. Output

### 5.1 Frame size

- **FR-19** All frames have the same size: the largest height and width over all valid planes.
  A smaller image is centered in the frame, with black margins.
- **FR-19a** Maximum frame size: the height and the width of a plane's image may not exceed
  **twice the diagonal of the volume**, `2·√(sx² + sy² + sz²)` (about 1732 for a 500³ volume).
  A larger plane is invalid (FR-9).
  - *Reason:* the part of any plane inside the volume is at most one diagonal long. A triangle
    must be larger than the region it covers, because its corners are empty: to cover a full
    slice it needs about twice the slice's size. Twice the diagonal is therefore enough for any
    useful plane, and it is derived from the volume rather than chosen arbitrarily. Without a
    limit, a valid plane far outside the volume could produce a frame thousands of pixels wide.

### 5.2 Intensity mapping

- **FR-20** Voxel values are mapped linearly to `0..255`, using one range for the whole video.
  - Default: the minimum and maximum of the whole volume.
  - Option: percentiles of the volume (e.g. 1% and 99%), so a few extreme voxels do not make
    the image dark.
  - *Rejected:* a range per frame. The same value would look different in different frames.

### 5.3 Video

- **FR-21** The video has one frame per CSV plane, in the CSV order.
- **FR-22** The video is grayscale, in MP4 format.
- **FR-22a** The playback rate is 10 frames per second by default, and can be changed from the
  command line.
  - *Reason:* a slower rate lets the viewer see each plane. This is the playback rate only; it
    is not related to the projection speed (NFR-1).

### 5.4 Report

- **FR-23** After the run the program prints:
  - the time to load the volume, in seconds;
  - **projection FPS**: frames per second for projection and intensity mapping;
  - **end-to-end FPS**: frames per second including writing the video.

## 6. Non-functional requirements

- **NFR-1 Performance:** on a 500³ volume of 8-bit voxels, projection FPS of at least **100**.
  The assignment's minimum is 30.
- **NFR-2 Correctness:** the fast implementation must give the same images as the simple
  loop-based reference implementation.
- **NFR-3 Robustness:** no input may crash the program with an unhandled exception.
- **NFR-4 Code quality:** object-oriented design, PEP 8, docstrings, automated tests.
- **NFR-5 Environment:** Python 3.10+, with NumPy and common libraries for NRRD and MP4.
